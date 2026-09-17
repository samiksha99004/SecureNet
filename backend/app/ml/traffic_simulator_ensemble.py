"""
Traffic Simulator for Ensemble Model
Generates 76 CICFlowMeter features
"""

import asyncio
import random
import numpy as np
from app.utils.logger import logger


class TrafficSimulatorEnsemble:
    """Simulates network traffic with 76 CICFlowMeter features"""
    
    def __init__(self, ids_service):
        self.ids_service = ids_service
        self.running = False
        self.flows_generated = 0
    
    def generate_benign_features(self):
        """Generate normal traffic with 76 CICFlowMeter features"""
        return np.array([
            # 1. Protocol
            6,  # TCP
            # 2. Flow Duration
            random.uniform(0.5, 5.0),
            # 3-4. Total Packets
            random.randint(10, 50),  # Total Fwd Packets
            random.randint(10, 50),  # Total Backward Packets
            # 5-6. Packet Length Totals
            random.randint(1000, 5000),  # Fwd Packets Length Total
            random.randint(2000, 10000),  # Bwd Packets Length Total
            # 7-10. Fwd Packet Length Stats
            random.randint(500, 1500),  # Max
            random.randint(40, 100),  # Min
            random.uniform(200, 800),  # Mean
            random.uniform(50, 300),  # Std
            # 11-14. Bwd Packet Length Stats
            random.randint(500, 1500),  # Max
            random.randint(40, 100),  # Min
            random.uniform(300, 1000),  # Mean
            random.uniform(100, 400),  # Std
            # 15-16. Flow Bytes/s and Packets/s
            random.uniform(1000, 10000),  # Flow Bytes/s
            random.uniform(5, 50),  # Flow Packets/s
            # 17-20. Flow IAT (Inter-Arrival Time)
            random.uniform(0.05, 0.3),  # Mean
            random.uniform(0.01, 0.1),  # Std
            random.uniform(0.2, 0.8),  # Max
            random.uniform(0.001, 0.05),  # Min
            # 21-25. Fwd IAT
            random.uniform(0.5, 3.0),  # Total
            random.uniform(0.05, 0.3),  # Mean
            random.uniform(0.01, 0.1),  # Std
            random.uniform(0.2, 0.8),  # Max
            random.uniform(0.001, 0.05),  # Min
            # 26-30. Bwd IAT
            random.uniform(0.5, 3.0),  # Total
            random.uniform(0.05, 0.3),  # Mean
            random.uniform(0.01, 0.1),  # Std
            random.uniform(0.2, 0.8),  # Max
            random.uniform(0.001, 0.05),  # Min
            # 31-34. PSH and URG Flags
            random.randint(1, 3),  # Fwd PSH Flags
            random.randint(1, 3),  # Bwd PSH Flags
            0,  # Fwd URG Flags
            0,  # Bwd URG Flags
            # 35-38. Header Lengths and Packet Rates
            random.randint(20, 60),  # Fwd Header Length
            random.randint(20, 60),  # Bwd Header Length
            random.uniform(5, 20),  # Fwd Packets/s
            random.uniform(5, 20),  # Bwd Packets/s
            # 39-43. Packet Length Stats
            random.randint(40, 100),  # Min
            random.randint(500, 1500),  # Max
            random.uniform(250, 900),  # Mean
            random.uniform(75, 350),  # Std
            random.uniform(5000, 120000),  # Variance
            # 44-51. TCP Flags
            random.randint(0, 2),  # FIN Flag Count
            random.randint(1, 2),  # SYN Flag Count
            0,  # RST Flag Count
            random.randint(1, 5),  # PSH Flag Count
            random.randint(5, 30),  # ACK Flag Count
            0,  # URG Flag Count
            0,  # CWE Flag Count
            0,  # ECE Flag Cnt
            # 52-54. Ratios and Sizes
            random.uniform(0.5, 2.0),  # Down/Up Ratio
            random.uniform(200, 800),  # Avg Packet Size
            random.uniform(200, 800),  # Avg Fwd Segment Size
            random.uniform(300, 1000),  # Avg Bwd Segment Size
            # 55-60. Bulk and Rates (usually 0 for normal traffic)
            0,  # Fwd Avg Bytes/Bulk
            0,  # Fwd Avg Packets/Bulk
            0,  # Fwd Avg Bulk Rate
            0,  # Bwd Avg Bytes/Bulk
            0,  # Bwd Avg Packets/Bulk
            0,  # Bwd Avg Bulk Rate
            # 61-64. Subflow Stats
            random.randint(10, 50),  # Subflow Fwd Packets
            random.randint(1000, 5000),  # Subflow Fwd Bytes
            random.randint(10, 50),  # Subflow Bwd Packets
            random.randint(2000, 10000),  # Subflow Bwd Bytes
            # 65-68. Window Bytes and Data Packets
            random.randint(8000, 65535),  # Init Fwd Win Bytes
            random.randint(8000, 65535),  # Init Bwd Win Bytes
            random.randint(5, 20),  # Fwd Act Data Packets
            random.randint(20, 60),  # Fwd Seg Size Min
            # 69-76. Active and Idle Times
            random.uniform(0.5, 2.0),  # Active Mean
            random.uniform(0.1, 0.5),  # Active Std
            random.uniform(1.0, 3.0),  # Active Max
            random.uniform(0.1, 0.5),  # Active Min
            random.uniform(0.1, 1.0),  # Idle Mean
            random.uniform(0.05, 0.3),  # Idle Std
            random.uniform(0.5, 2.0),  # Idle Max
            random.uniform(0.01, 0.1),  # Idle Min
        ], dtype=np.float32)
    
    def generate_attack_features(self, attack_type):
        """Generate attack traffic features"""
        features = self.generate_benign_features()
        
        if "DoS" in attack_type or "DDoS" in attack_type:
            # High packet rate, short duration
            features[1] = random.uniform(0.001, 0.1)  # Flow Duration - very short
            features[2] = random.randint(100, 500)  # Total Fwd Packets - many
            features[3] = random.randint(0, 5)  # Total Backward Packets - few/none
            features[15] = random.uniform(10000, 100000)  # Flow Packets/s - very high
            features[16] = random.uniform(0.0001, 0.001)  # Flow IAT Mean - very fast
            features[14] = random.uniform(50000, 500000)  # Flow Bytes/s - very high
            
        elif "Brute" in attack_type:
            # Repeated connection attempts
            features[1] = random.uniform(0.5, 2.0)  # Flow Duration
            features[2] = random.randint(20, 50)  # Total Fwd Packets
            features[37] = random.uniform(10, 30)  # Fwd Packets/s
            features[31] = random.randint(3, 8)  # Fwd PSH Flags - more pushes
            features[44] = random.randint(5, 15)  # FIN Flag Count - many connection closes
            
        elif "Bot" in attack_type:
            # Automated, regular patterns
            features[1] = random.uniform(2.0, 10.0)  # Flow Duration - longer
            features[2] = random.randint(100, 300)  # Total Fwd Packets - many
            features[3] = random.randint(100, 300)  # Total Backward Packets
            features[15] = random.uniform(50, 100)  # Flow Packets/s - high but steady
            features[16] = random.uniform(0.01, 0.05)  # Flow IAT Mean - very regular
            features[17] = random.uniform(0.001, 0.01)  # Flow IAT Std - low variance
            
        elif "Infiltration" in attack_type:
            # Slow, stealthy
            features[1] = random.uniform(10.0, 60.0)  # Flow Duration - very long
            features[15] = random.uniform(1, 5)  # Flow Packets/s - very slow
            features[2] = random.randint(5, 20)  # Total Fwd Packets - few
            features[16] = random.uniform(1.0, 5.0)  # Flow IAT Mean - slow
        
        return features
    
    async def run(self, benign_ratio=0.6, interval=3.0):
        """Run traffic simulation"""
        logger.info(f"🚀 Traffic simulator started (Ensemble) (benign_ratio={benign_ratio}, interval={interval}s)")
        
        internal_ips = ["192.168.1.100", "192.168.1.101", "10.0.0.10", "172.16.0.50"]
        external_ips = ["8.8.8.8", "1.1.1.1", "142.250.185.46", "151.101.1.140"]
        attack_ips = ["203.0.113.45", "198.51.100.23", "192.0.2.100", "185.220.101.50"]
        
        # Common attack types from CIC-IDS2018
        attack_types = [
            "Bot",
            "DDoS Attack",
            "DoS Attack",
            "Brute Force",
            "Infiltration"
        ]
        
        while self.running:
            try:
                # Generate flow
                if random.random() < benign_ratio:
                    # Benign traffic
                    features = self.generate_benign_features()
                    src_ip = random.choice(internal_ips)
                    dst_ip = random.choice(external_ips)
                    flow_type = "Benign"
                else:
                    # Attack traffic
                    attack_type = random.choice(attack_types)
                    features = self.generate_attack_features(attack_type)
                    src_ip = random.choice(attack_ips)
                    dst_ip = random.choice(internal_ips)
                    flow_type = f"Attack-{attack_type}"
                
                # Extract protocol and ports from features
                protocol = int(features[0])  # Protocol
                dst_port = random.choice([80, 443, 22, 3389, 3306, 21]) if "Brute" in flow_type else random.choice([80, 443, 53])
                src_port = random.randint(49152, 65535)
                
                # Feed to IDS
                await self.ids_service.process_flow(
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=src_port,
                    dst_port=dst_port,
                    protocol=protocol,
                    features=features
                )
                
                self.flows_generated += 1
                
                if self.flows_generated % 5 == 0:
                    logger.info(f"📊 Simulator (Ensemble): {self.flows_generated} flows ({flow_type})")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Simulator error: {e}", exc_info=True)
                await asyncio.sleep(interval)
        
        logger.info(f"🛑 Traffic simulator stopped ({self.flows_generated} flows generated)")
    
    def stop(self):
        """Stop the simulator"""
        self.running = False


# Global instance
_simulator = None


async def start_simulator_async(ids_service, benign_ratio=0.6, interval=3.0):
    """Start the traffic simulator"""
    global _simulator
    
    if _simulator and _simulator.running:
        logger.warning("Simulator already running")
        return
    
    _simulator = TrafficSimulatorEnsemble(ids_service)
    _simulator.running = True
    await _simulator.run(benign_ratio, interval)


def stop_simulator():
    """Stop the traffic simulator"""
    global _simulator
    if _simulator:
        _simulator.stop()
