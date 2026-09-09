"""
SecureNet IDS Service - Complete Detection Pipeline

Orchestrates:
1. Network monitoring
2. Feature extraction
3. ML inference (Isolation Forest + XGBoost)
4. Security event creation
5. Protection actions
6. Database persistence
7. WebSocket broadcasting
"""

import asyncio
import threading
import numpy as np
import pandas as pd
from typing import Optional, Dict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.models import get_ml_models
from app.ml.network_monitor import NetworkMonitor, FlowKey
from app.models.security_event import (
    SecurityEvent, SeverityLevel, EventState, DetectionMode,
    ActionTaken, Protocol
)
# ProtectionMode not used - IDS ON automatically enables protection
from app.db.base import AsyncSessionLocal
from app.websocket.manager import manager
from app.utils.logger import logger


class IDSService:
    """Main IDS detection and protection service"""
    
    def __init__(self):
        self.enabled = False
        self.monitor = None
        self.ml_models = get_ml_models()
        self.monitoring_thread = None
        self.mode = DetectionMode.MONITOR
        self.whitelist_ips = set()
        
        # Statistics
        self.packets_processed = 0
        self.flows_analyzed = 0
        self.anomalies_detected = 0
        self.attacks_detected = 0
    
    async def initialize(self):
        """Initialize the IDS service"""
        logger.info("Initializing IDS service...")
        
        # Load ML models
        if not self.ml_models.loaded:
            success = self.ml_models.load_models()
            if not success:
                logger.error("Failed to load ML models - IDS cannot start")
                return False
        
        logger.info("IDS service initialized successfully")
        return True
    
    def is_enabled(self) -> bool:
        """Check if IDS is currently enabled"""
        return self.enabled
    
    def get_status(self) -> Dict:
        """Get current IDS status"""
        return {
            "enabled": self.enabled,
            "mode": self.mode.value if self.mode else "monitor",
            "ml_loaded": self.ml_models.loaded,
            "packets_processed": self.packets_processed,
            "flows_analyzed": self.flows_analyzed,
            "anomalies_detected": self.anomalies_detected,
            "attacks_detected": self.attacks_detected,
        }
    
    async def start(self):
        """Start IDS monitoring and detection"""
        if self.enabled:
            logger.warning("IDS already enabled")
            return True
        
        if not self.ml_models.loaded:
            logger.error("Cannot start IDS - ML models not loaded")
            return False
        
        logger.info("Starting IDS...")
        
        # Create network monitor
        self.monitor = NetworkMonitor(callback=self._on_flow_ready)
        
        # Start monitoring in background thread
        self.enabled = True
        self.monitoring_thread = threading.Thread(target=self._run_monitoring, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("✓ IDS started successfully")
        return True
    
    async def stop(self):
        """Stop IDS monitoring and detection"""
        if not self.enabled:
            logger.warning("IDS already disabled")
            return True
        
        logger.info("Stopping IDS...")
        
        self.enabled = False
        
        if self.monitor:
            self.monitor.stop()
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        logger.info("✓ IDS stopped successfully")
        return True
    
    def _run_monitoring(self):
        """Run network monitoring (blocking, runs in thread)"""
        try:
            if self.monitor:
                self.monitor.start()
                self.monitor.capture_packets()
        except Exception as e:
            logger.error(f"Monitoring thread error: {e}", exc_info=True)
            self.enabled = False
    
    def _on_flow_ready(self, flow_key: FlowKey, features: Dict[str, float]):
        """
        Callback when a flow has enough packets for analysis
        This runs in the monitoring thread
        """
        try:
            # Run detection in async context
            asyncio.run(self._analyze_flow(flow_key, features))
        except Exception as e:
            logger.error(f"Flow analysis error: {e}", exc_info=True)
    
    async def _analyze_flow(self, flow_key: FlowKey, features: Dict[str, float]):
        """Analyze a flow through the ML pipeline"""
        try:
            self.flows_analyzed += 1
            
            # Check whitelist
            if flow_key.src_ip in self.whitelist_ips or flow_key.dst_ip in self.whitelist_ips:
                logger.debug(f"Flow whitelisted: {flow_key.src_ip} -> {flow_key.dst_ip}")
                return
            
            # Convert features to the exact format expected by ML models
            feature_names = self.ml_models.get_feature_names()
            if not feature_names:
                logger.error("Feature names not available")
                return
            
            # Build feature vector in correct order
            feature_vector = []
            for fname in feature_names:
                feature_vector.append(features.get(fname, 0.0))
            
            # Convert to numpy array
            X = np.array([feature_vector], dtype=np.float32)
            
            # Replace inf values with NaN (XGBoost handles NaN natively)
            X = np.where(np.isinf(X), np.nan, X)
            
            # Stage 1: Isolation Forest (Anomaly Detection)
            if_scores, is_anomalies = self.ml_models.predict_anomaly(X)
            anomaly_score = float(if_scores[0])
            is_anomaly = bool(is_anomalies[0])
            
            if not is_anomaly:
                # Normal traffic - no alert needed
                return
            
            # Anomaly detected!
            self.anomalies_detected += 1
            logger.info(f"Anomaly detected: {flow_key.src_ip} -> {flow_key.dst_ip}, score={anomaly_score:.4f}")
            
            # Stage 2: Binary classification (normal/attack)
            binary_preds, binary_probs = self.ml_models.predict_binary(X, if_scores)
            is_attack = bool(binary_preds[0])
            attack_probability = float(binary_probs[0])
            
            if not is_attack:
                # Anomaly but not classified as attack
                logger.debug(f"Anomaly classified as non-attack (prob={attack_probability:.4f})")
                return
            
            # Attack detected!
            self.attacks_detected += 1
            
            # Stage 3: Multi-class classification (attack type)
            attack_type = "UNKNOWN ATTACK TYPE"
            confidence = 0.0
            
            try:
                if self.ml_models.xgboost_multiclass and self.ml_models.label_encoder:
                    _, predicted_labels, confidences = self.ml_models.predict_multiclass(X, if_scores)
                    predicted_label = predicted_labels[0]
                    
                    # Only use classification if it's not "Benign" and has reasonable confidence
                    if predicted_label != "Benign" and confidences[0] > 0.3:
                        attack_type = predicted_label
                        confidence = float(confidences[0])
                    else:
                        attack_type = "UNKNOWN ATTACK TYPE"
                        confidence = 0.0
            except Exception as e:
                logger.warning(f"Attack classification failed: {e}")
                attack_type = "UNKNOWN ATTACK TYPE"
                confidence = 0.0
            
            # Determine severity based on anomaly score
            if anomaly_score < -0.5:
                severity = SeverityLevel.HIGH
            elif anomaly_score < -0.2:
                severity = SeverityLevel.MEDIUM
            else:
                severity = SeverityLevel.LOW
            
            # Determine protocol enum
            proto_map = {
                'TCP': Protocol.TCP,
                'UDP': Protocol.UDP,
                'ICMP': Protocol.ICMP
            }
            protocol = proto_map.get(flow_key.protocol, Protocol.OTHER)
            
            # Create security event
            event = SecurityEvent(
                timestamp=datetime.utcnow(),
                source_ip=flow_key.src_ip,
                source_port=flow_key.src_port,
                destination_ip=flow_key.dst_ip,
                destination_port=flow_key.dst_port,
                protocol=protocol,
                anomaly_score=abs(anomaly_score),  # Make positive for display
                severity=severity,
                attack_type=attack_type if attack_type != "UNKNOWN ATTACK TYPE" else None,
                confidence=confidence if confidence > 0 else None,
                mode=self.mode,
                state=EventState.ACTIVE,
                action_taken=ActionTaken.LOGGED,
                detection_reason=f"Isolation Forest anomaly score: {anomaly_score:.4f}, Binary classification probability: {attack_probability:.4f}",
                contributing_features=None,  # Could add top features
            )
            
            # Perform protection action if in protect mode
            if self.mode == DetectionMode.PROTECT and severity == SeverityLevel.HIGH:
                blocked = await self._block_ip(flow_key.src_ip)
                if blocked:
                    event.action_taken = ActionTaken.BLOCKED
            
            # Save to database
            async with AsyncSessionLocal() as db:
                db.add(event)
                await db.commit()
                await db.refresh(event)
                
                # Broadcast to WebSocket clients
                await manager.send_live_score({
                    "anomalyScore": abs(anomaly_score),
                    "severity": severity.value,
                    "sourceIp": flow_key.src_ip,
                    "destinationIp": flow_key.dst_ip,
                    "protocol": protocol.value,
                    "attackType": attack_type,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "eventId": str(event.id),
                })
                
                logger.info(f"Security event created: {attack_type} from {flow_key.src_ip} (severity={severity.value})")
        
        except Exception as e:
            logger.error(f"Flow analysis pipeline error: {e}", exc_info=True)
    
    async def _block_ip(self, ip_address: str) -> bool:
        """
        Attempt to block an IP address using Windows Firewall
        Returns True if successful, False otherwise
        """
        try:
            import subprocess
            
            # Windows Firewall command
            rule_name = f"SecureNet_Block_{ip_address.replace('.', '_')}"
            cmd = [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={rule_name}",
                "dir=in",
                "action=block",
                f"remoteip={ip_address}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                logger.info(f"✓ Blocked IP: {ip_address}")
                return True
            else:
                logger.warning(f"✗ Failed to block IP {ip_address}: {result.stderr}")
                return False
        
        except Exception as e:
            logger.error(f"Error blocking IP {ip_address}: {e}")
            return False
    
    async def update_whitelist(self, whitelist_ips: set):
        """Update the whitelist of IPs that should not be blocked"""
        self.whitelist_ips = whitelist_ips
        logger.info(f"Whitelist updated: {len(whitelist_ips)} entries")
    
    async def set_mode(self, mode: str):
        """Set detection/protection mode"""
        if mode == "monitor":
            self.mode = DetectionMode.MONITOR
        elif mode == "protect":
            self.mode = DetectionMode.PROTECT
        else:
            logger.warning(f"Unknown mode: {mode}")
            return False
        
        logger.info(f"IDS mode set to: {mode}")
        return True


# Global IDS service instance
ids_service = IDSService()


async def initialize_ids() -> bool:
    """Initialize IDS service on startup"""
    return await ids_service.initialize()


def get_ids_service() -> IDSService:
    """Get the global IDS service instance"""
    return ids_service
