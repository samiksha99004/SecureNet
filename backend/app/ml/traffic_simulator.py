"""
Network Traffic Simulator - Integrated with IDS
Generates realistic network flows for ML analysis
"""

import asyncio
import random
import numpy as np
from app.utils.logger import logger


class TrafficSimulator:
    """Simulates network traffic"""
    
    def __init__(self, ids_service):
        self.ids_service = ids_service
        self.running = False
        self.flows_generated = 0
    
    def generate_benign_features(self):
        """Generate normal traffic 71 features matching model expectations"""
        return np.array([
            # 1. Dst Port
            random.choice([80, 443, 53, 8080]),
            # 2. Flow Duration
            random.uniform(0.5, 5.0),
            # 3. Tot Fwd Pkts
            random.randint(10, 50),
            # 4. Tot Bwd Pkts
            random.randint(10, 50),
            # 5. TotLen Fwd Pkts
            random.randint(1000, 5000),
            # 6. TotLen Bwd Pkts
            random.randint(2000, 10000),
            # 7. Fwd Pkt Len Max
            random.randint(500, 1500),
            # 8. Fwd Pkt Len Min
            random.randint(40, 100),
            # 9. Fwd Pkt Len Mean
            random.uniform(200, 800),
            # 10. Fwd Pkt Len Std
            random.uniform(50, 300),
            # 11. Bwd Pkt Len Max
            random.randint(500, 1500),
            # 12. Bwd Pkt Len Min
            random.randint(40, 100),
            # 13. Bwd Pkt Len Mean
            random.uniform(300, 1000),
            # 14. Bwd Pkt Len Std
            random.uniform(100, 400),
            # 15. Flow Byts/s
            random.uniform(1000, 10000),
            # 16. Flow Pkts/s
            random.uniform(5, 50),
            # 17. Flow IAT Mean
            random.uniform(0.05, 0.3),
            # 18. Flow IAT Std
            random.uniform(0.01, 0.1),
            # 19. Flow IAT Max
            random.uniform(0.2, 0.8),
            # 20. Flow IAT Min
            random.uniform(0.001, 0.05),
            # 21. Fwd IAT Tot
            random.uniform(0.5, 3.0),
            # 22. Fwd IAT Mean
            random.uniform(0.05, 0.3),
            # 23. Fwd IAT Std
            random.uniform(0.01, 0.1),
            # 24. Fwd IAT Max
            random.uniform(0.2, 0.8),
            # 25. Fwd IAT Min
            random.uniform(0.001, 0.05),
            # 26. Bwd IAT Tot
            random.uniform(0.5, 3.0),
            # 27. Bwd IAT Mean
            random.uniform(0.05, 0.3),
            # 28. Bwd IAT Std
            random.uniform(0.01, 0.1),
            # 29. Bwd IAT Max
            random.uniform(0.2, 0.8),
            # 30. Bwd IAT Min
            random.uniform(0.001, 0.05),
            # 31. Fwd PSH Flags
            random.randint(1, 3),
            # 32. Fwd Header Len
            random.randint(20, 60),
            # 33. Bwd Header Len
            random.randint(20, 60),
            # 34. Fwd Pkts/s
            random.uniform(5, 20),
            # 35. Bwd Pkts/s
            random.uniform(5, 20),
            # 36. Pkt Len Min
            random.randint(40, 100),
            # 37. Pkt Len Max
            random.randint(500, 1500),
            # 38. Pkt Len Mean
            random.uniform(250, 900),
            # 39. Pkt Len Std
            random.uniform(75, 350),
            # 40. Pkt Len Var
            random.uniform(5000, 120000),
            # 41. FIN Flag Cnt
            random.randint(0, 2),
            # 42. SYN Flag Cnt
            random.randint(1, 2),
            # 43. RST Flag Cnt
            0,
            # 44. PSH Flag Cnt
            random.randint(1, 5),
            # 45. ACK Flag Cnt
            random.randint(5, 30),
            # 46. URG Flag Cnt
            0,
            # 47. CWE Flag Count
            0,
            # 48. ECE Flag Cnt
            0,
            # 49. Down/Up Ratio
            random.uniform(0.5, 2.0),
            # 50. Pkt Size Avg
            random.uniform(200, 800),
            # 51. Fwd Seg Size Avg
            random.uniform(200, 800),
            # 52. Bwd Seg Size Avg
            random.uniform(300, 1000),
            # 53. Subflow Fwd Pkts
            random.randint(10, 50),
            # 54. Subflow Fwd Byts
            random.randint(1000, 5000),
            # 55. Subflow Bwd Pkts
            random.randint(10, 50),
            # 56. Subflow Bwd Byts
            random.randint(2000, 10000),
            # 57. Init Fwd Win Byts
            random.randint(8000, 65535),
            # 58. Init Bwd Win Byts
            random.randint(8000, 65535),
            # 59. Fwd Act Data Pkts
            random.randint(5, 20),
            # 60. Fwd Seg Size Min
            random.randint(20, 60),
            # 61. Active Mean
            random.uniform(0.5, 2.0),
            # 62. Active Std
            random.uniform(0.1, 0.5),
            # 63. Active Max
            random.uniform(1.0, 3.0),
            # 64. Active Min
            random.uniform(0.1, 0.5),
            # 65. Idle Mean
            random.uniform(0.1, 1.0),
            # 66. Idle Std
            random.uniform(0.05, 0.3),
            # 67. Idle Max
            random.uniform(0.5, 2.0),
            # 68. Idle Min
            random.uniform(0.01, 0.1),
            # 69. Protocol_0 (OTHER)
            0,
            # 70. Protocol_6 (TCP)
            1,
            # 71. Protocol_17 (UDP)
            0,
        ], dtype=np.float32)
    
    def generate_attack_features(self, attack_type):
        """Generate attack traffic features"""
        features = self.generate_benign_features()
        
        if attack_type == 'DoS':
            # High packet rate, short duration, no responses
            features[1] = random.uniform(0.001, 0.1)  # Flow Duration - very short
            features[2] = random.randint(1, 5)  # Tot Fwd Pkts - few packets
            features[3] = 0  # Tot Bwd Pkts - no response
            features[15] = random.uniform(1000, 10000)  # Flow Pkts/s - very high rate
            features[16] = random.uniform(0.0001, 0.001)  # Flow IAT Mean - very fast
            
        elif attack_type == 'Port Scan':
            # Many short connections to different ports
            features[0] = random.randint(1, 1024)  # Dst Port - scanning low ports
            features[1] = random.uniform(0.001, 0.05)  # Flow Duration - very short
            features[2] = 1  # Tot Fwd Pkts - SYN only
            features[3] = random.choice([0, 1])  # Tot Bwd Pkts - may not respond
            features[34] = random.uniform(100, 1000)  # Fwd Pkts/s - high scan rate
            
        elif attack_type == 'Brute Force':
            # Repeated connection attempts
            features[0] = random.choice([22, 21, 3389])  # Dst Port - SSH, FTP, RDP
            features[1] = random.uniform(0.5, 2.0)  # Flow Duration
            features[2] = random.randint(10, 30)  # Tot Fwd Pkts - multiple attempts
            features[34] = random.uniform(5, 15)  # Fwd Pkts/s - moderate rate
            features[31] = random.randint(2, 5)  # Fwd PSH Flags
            
        elif attack_type == 'Bot':
            # Automated, regular patterns
            features[1] = random.uniform(1.0, 10.0)  # Flow Duration - longer
            features[2] = random.randint(50, 200)  # Tot Fwd Pkts - many packets
            features[3] = random.randint(50, 200)  # Tot Bwd Pkts
            features[34] = random.uniform(20, 100)  # Fwd Pkts/s - high but steady
            features[16] = random.uniform(0.01, 0.05)  # Flow IAT Mean - very regular
            features[17] = random.uniform(0.001, 0.01)  # Flow IAT Std - low variance (robotic)
        
        return features
    
    async def run(self, benign_ratio=0.7, interval=2.0):
        """Run traffic simulation"""
        logger.info(f"🚀 Traffic simulator started (benign_ratio={benign_ratio}, interval={interval}s)")
        
        internal_ips = ["192.168.1.100", "192.168.1.101", "10.0.0.10", "172.16.0.50"]
        external_ips = ["8.8.8.8", "1.1.1.1", "142.250.185.46", "151.101.1.140"]
        attack_ips = ["203.0.113.45", "198.51.100.23", "192.0.2.100", "185.220.101.50"]
        attack_types = ['DoS', 'Port Scan', 'Brute Force', 'Bot']
        
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
                
                # Extract ports from features
                dst_port = int(features[0])  # Dst Port (index 0)
                
                # Protocol is one-hot encoded in features 68-70 (0-indexed)
                # Index 68: Protocol_0=OTHER, Index 69: Protocol_6=TCP, Index 70: Protocol_17=UDP
                if features[69] == 1:  # Protocol_6 (TCP)
                    protocol = 6
                elif features[70] == 1:  # Protocol_17 (UDP)
                    protocol = 17
                else:  # Protocol_0 (OTHER/ICMP)
                    protocol = 1
                
                src_port = random.randint(49152, 65535)
                
                # Feed to IDS
                await self.ids_service._process_flow(
                    src_ip=src_ip,
                    dst_ip=dst_ip,
                    src_port=src_port,
                    dst_port=dst_port,
                    protocol=protocol,
                    features=features
                )
                
                self.flows_generated += 1
                
                if self.flows_generated % 10 == 0:
                    logger.info(f"📊 Simulator: {self.flows_generated} flows ({flow_type})")
                
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


async def start_simulator_async(ids_service, benign_ratio=0.7, interval=2.0):
    """Start the traffic simulator"""
    global _simulator
    
    if _simulator and _simulator.running:
        logger.warning("Simulator already running")
        return
    
    _simulator = TrafficSimulator(ids_service)
    _simulator.running = True
    await _simulator.run(benign_ratio, interval)


def stop_simulator():
    """Stop the traffic simulator"""
    global _simulator
    if _simulator:
        _simulator.stop()
