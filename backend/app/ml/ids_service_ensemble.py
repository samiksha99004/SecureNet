"""
IDS Service - Ensemble Model Version
Simplified service using Random Forest + XGBoost ensemble
"""

import asyncio
from datetime import datetime
from typing import Dict
import numpy as np

from app.ml.models_ensemble import get_ml_models
from app.models.security_event import SecurityEvent, SeverityLevel, EventState, DetectionMode, ActionTaken, Protocol
from app.db.base import AsyncSessionLocal
from app.websocket.manager import manager
from app.utils.logger import logger


class IDSServiceEnsemble:
    """IDS service using ensemble model"""
    
    def __init__(self):
        self.enabled = False
        self.ml_models = get_ml_models()
        self.mode = DetectionMode.PROTECT
        self.whitelist_ips = set()
        
        # Statistics
        self.packets_processed = 0
        self.flows_analyzed = 0
        self.anomalies_detected = 0
        self.attacks_detected = 0
    
    async def initialize(self) -> bool:
        """Initialize the IDS service"""
        logger.info("Initializing IDS service (Ensemble)...")
        
        if not self.ml_models.loaded:
            success = self.ml_models.load_models()
            if not success:
                logger.error("Failed to load ML models")
                return False
        
        logger.info("✓ IDS service initialized (Ensemble)")
        return True
    
    def is_enabled(self) -> bool:
        """Check if IDS is enabled"""
        return self.enabled
    
    def get_status(self) -> Dict:
        """Get current IDS status"""
        return {
            "enabled": self.enabled,
            "mode": self.mode.value if self.mode else "protect",
            "ml_loaded": self.ml_models.loaded,
            "packets_processed": self.packets_processed,
            "flows_analyzed": self.flows_analyzed,
            "anomalies_detected": self.anomalies_detected,
            "attacks_detected": self.attacks_detected,
        }
    
    async def start(self) -> bool:
        """Start IDS"""
        if self.enabled:
            logger.warning("IDS already enabled")
            return True
        
        if not self.ml_models.loaded:
            logger.error("Cannot start IDS - ML models not loaded")
            return False
        
        logger.info("Starting IDS (Ensemble)...")
        self.enabled = True
        
        # Start traffic simulator
        await self._start_simulator()
        
        logger.info("✓ IDS started successfully (Ensemble)")
        return True
    
    async def stop(self) -> bool:
        """Stop IDS"""
        if not self.enabled:
            logger.warning("IDS already disabled")
            return True
        
        logger.info("Stopping IDS...")
        self.enabled = False
        
        # Stop simulator
        try:
            from app.ml.traffic_simulator_ensemble import stop_simulator
            stop_simulator()
        except Exception as e:
            logger.debug(f"No simulator to stop: {e}")
        
        logger.info("✓ IDS stopped successfully")
        return True
    
    async def _start_simulator(self):
        """Start the traffic simulator"""
        try:
            from app.ml.traffic_simulator_ensemble import start_simulator_async
            # Start simulator with 60% benign, 40% attacks for demonstration
            asyncio.create_task(start_simulator_async(
                ids_service=self,
                benign_ratio=0.6,
                interval=3.0  # Every 3 seconds
            ))
            logger.info("✓ Traffic simulator started (Ensemble)")
        except Exception as e:
            logger.error(f"Failed to start simulator: {e}", exc_info=True)
    
    async def process_flow(self, src_ip: str, dst_ip: str, src_port: int, dst_port: int, protocol: int, features: np.ndarray):
        """
        Process a network flow through ML detection
        features: numpy array with 76 CICFlowMeter features
        """
        try:
            self.packets_processed += 1
            self.flows_analyzed += 1
            
            # Check whitelist
            if src_ip in self.whitelist_ips or dst_ip in self.whitelist_ips:
                return
            
            # Predict using ensemble
            label, confidence, threat_score = self.ml_models.predict(features)
            
            # Determine if it's an attack
            is_attack = label != "Benign"
            
            if is_attack:
                self.attacks_detected += 1
                self.anomalies_detected += 1
            elif threat_score > 0.3:
                # High threat score even if classified as Benign
                self.anomalies_detected += 1
            
            # Only save attacks to database
            if not is_attack:
                return
            
            # Determine severity
            if threat_score >= 0.7:
                severity = SeverityLevel.HIGH
            elif threat_score >= 0.4:
                severity = SeverityLevel.MEDIUM
            else:
                severity = SeverityLevel.LOW
            
            # Determine protocol enum
            proto_map = {6: Protocol.TCP, 17: Protocol.UDP, 1: Protocol.ICMP}
            protocol_enum = proto_map.get(protocol, Protocol.OTHER)
            
            # Create security event
            event = SecurityEvent(
                timestamp=datetime.utcnow(),
                source_ip=src_ip,
                source_port=src_port,
                destination_ip=dst_ip,
                destination_port=dst_port,
                protocol=protocol_enum,
                anomaly_score=threat_score,  # Use threat score as anomaly score
                severity=severity,
                attack_type=label,
                confidence=confidence,
                mode=self.mode,
                state=EventState.ACTIVE,
                action_taken=ActionTaken.LOGGED,
                detection_reason=f"Ensemble ML: {label} (confidence={confidence:.2f}, threat={threat_score:.2f})",
                contributing_features=None,
            )
            
            # Block if high severity and in protect mode
            if self.mode == DetectionMode.PROTECT and severity == SeverityLevel.HIGH:
                # Note: Actual blocking would require admin privileges
                event.action_taken = ActionTaken.BLOCKED
            
            # Save to database
            async with AsyncSessionLocal() as db:
                db.add(event)
                await db.commit()
                await db.refresh(event)
                
                # Broadcast to WebSocket
                await manager.send_live_score({
                    "anomalyScore": threat_score,
                    "severity": severity.value,
                    "sourceIp": src_ip,
                    "destinationIp": dst_ip,
                    "protocol": protocol_enum.value,
                    "attackType": label,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "eventId": str(event.id),
                })
                
                logger.info(f"🚨 Attack detected: {label} from {src_ip} (confidence={confidence:.2f}, threat={threat_score:.2f}, severity={severity.value})")
        
        except Exception as e:
            logger.error(f"Flow processing error: {e}", exc_info=True)
    
    async def set_mode(self, mode: str) -> bool:
        """Set detection mode"""
        if mode == "monitor":
            self.mode = DetectionMode.MONITOR
        elif mode == "protect":
            self.mode = DetectionMode.PROTECT
        else:
            logger.warning(f"Unknown mode: {mode}")
            return False
        
        logger.info(f"IDS mode set to: {mode}")
        return True
    
    async def update_whitelist(self, whitelist_ips: set):
        """Update whitelist"""
        self.whitelist_ips = whitelist_ips
        logger.info(f"Whitelist updated: {len(whitelist_ips)} entries")


# Global instance
_ids_service = IDSServiceEnsemble()


async def initialize_ids() -> bool:
    """Initialize IDS service"""
    return await _ids_service.initialize()


def get_ids_service() -> IDSServiceEnsemble:
    """Get global IDS service instance"""
    return _ids_service
