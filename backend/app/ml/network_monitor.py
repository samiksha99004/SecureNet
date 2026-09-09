"""
SecureNet Network Monitor - Real Packet Capture

Captures real network traffic using Scapy and extracts the exact 71 features
required by the trained ML models.
"""

import asyncio
import time
from typing import Dict, Optional, Callable
from datetime import datetime
from collections import defaultdict
import numpy as np

try:
    from scapy.all import sniff, IP, TCP, UDP, ICMP
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    IP = TCP = UDP = ICMP = None

from app.utils.logger import logger


class FlowKey:
    """Represents a network flow (5-tuple)"""
    def __init__(self, src_ip, dst_ip, src_port, dst_port, protocol):
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.src_port = src_port
        self.dst_port = dst_port
        self.protocol = protocol
    
    def __hash__(self):
        return hash((self.src_ip, self.dst_ip, self.src_port, self.dst_port, self.protocol))
    
    def __eq__(self, other):
        return (self.src_ip == other.src_ip and
                self.dst_ip == other.dst_ip and
                self.src_port == other.src_port and
                self.dst_port == other.dst_port and
                self.protocol == other.protocol)


class NetworkFlow:
    """Tracks statistics for a single network flow"""
    
    def __init__(self, flow_key: FlowKey):
        self.flow_key = flow_key
        self.start_time = time.time()
        self.last_packet_time = self.start_time
        
        # Packet counts
        self.fwd_packets = []
        self.bwd_packets = []
        
        # Byte counts
        self.fwd_bytes = []
        self.bwd_bytes = []
        
        # Packet lengths
        self.fwd_pkt_lens = []
        self.bwd_pkt_lens = []
        
        # Inter-arrival times
        self.fwd_iat = []
        self.bwd_iat = []
        
        # Flags
        self.fin_count = 0
        self.syn_count = 0
        self.rst_count = 0
        self.psh_count = 0
        self.ack_count = 0
        self.urg_count = 0
        self.ece_count = 0
        self.cwr_count = 0
        
        # Active/Idle times
        self.active_times = []
        self.idle_times = []
        self.last_active_time = self.start_time
    
    def add_packet(self, packet, is_forward: bool, timestamp: float):
        """Add a packet to the flow"""
        pkt_len = len(packet)
        
        if is_forward:
            self.fwd_packets.append(timestamp)
            self.fwd_bytes.append(pkt_len)
            self.fwd_pkt_lens.append(pkt_len)
            
            if len(self.fwd_packets) > 1:
                iat = timestamp - self.fwd_packets[-2]
                self.fwd_iat.append(iat)
        else:
            self.bwd_packets.append(timestamp)
            self.bwd_bytes.append(pkt_len)
            self.bwd_pkt_lens.append(pkt_len)
            
            if len(self.bwd_packets) > 1:
                iat = timestamp - self.bwd_packets[-2]
                self.bwd_iat.append(iat)
        
        # Track TCP flags
        if TCP in packet:
            tcp_layer = packet[TCP]
            if tcp_layer.flags.F: self.fin_count += 1
            if tcp_layer.flags.S: self.syn_count += 1
            if tcp_layer.flags.R: self.rst_count += 1
            if tcp_layer.flags.P: self.psh_count += 1
            if tcp_layer.flags.A: self.ack_count += 1
            if tcp_layer.flags.U: self.urg_count += 1
            if tcp_layer.flags.E: self.ece_count += 1
            if tcp_layer.flags.C: self.cwr_count += 1
        
        # Track active/idle
        time_since_last = timestamp - self.last_active_time
        if time_since_last > 1.0:  # 1 second idle threshold
            self.idle_times.append(time_since_last)
        else:
            self.active_times.append(time_since_last)
        
        self.last_active_time = timestamp
        self.last_packet_time = timestamp
    
    def extract_features(self) -> Dict[str, float]:
        """
        Extract the exact 71 features expected by the trained model
        
        Feature list from F:\all_10_csv_manual\feature_columns.pkl:
        1. Dst Port
        2. Flow Duration
        3. Tot Fwd Pkts
        4. Tot Bwd Pkts
        5. TotLen Fwd Pkts
        6. TotLen Bwd Pkts
        7-10. Fwd Pkt Len Max/Min/Mean/Std
        11-14. Bwd Pkt Len Max/Min/Mean/Std
        15. Flow Byts/s
        16. Flow Pkts/s
        17-20. Flow IAT Mean/Std/Max/Min
        21-24. Fwd IAT Tot/Mean/Std/Max/Min
        25-28. Bwd IAT Tot/Mean/Std/Max/Min
        29-36. Fwd/Bwd PSH/URG Flags
        37-38. Fwd/Bwd Header Len
        39-40. Fwd/Bwd Pkts/s
        41. Pkt Len Min/Max/Mean/Std/Var
        42-49. FIN/SYN/RST/PSH/ACK/URG/CWE/ECE Flag Cnt
        50. Down/Up Ratio
        51. Pkt Size Avg
        52-55. Fwd/Bwd Seg Size Avg
        56-59. Fwd/Bwd Byts/b Avg
        60-63. Fwd/Bwd Pkts/b Avg
        64-67. Fwd/Bwd Blk Rate Avg
        68-71. Subflow Fwd/Bwd Pkts/Byts
        Plus init window sizes and active/idle stats
        """
        
        duration = self.last_packet_time - self.start_time
        if duration == 0:
            duration = 0.000001  # Avoid division by zero
        
        total_fwd_pkts = len(self.fwd_packets)
        total_bwd_pkts = len(self.bwd_packets)
        total_fwd_bytes = sum(self.fwd_bytes) if self.fwd_bytes else 0
        total_bwd_bytes = sum(self.bwd_bytes) if self.bwd_bytes else 0
        
        # Calculate statistics
        def safe_stats(data):
            if not data or len(data) == 0:
                return 0, 0, 0, 0  # min, max, mean, std
            arr = np.array(data)
            return float(np.min(arr)), float(np.max(arr)), float(np.mean(arr)), float(np.std(arr))
        
        fwd_min, fwd_max, fwd_mean, fwd_std = safe_stats(self.fwd_pkt_lens)
        bwd_min, bwd_max, bwd_mean, bwd_std = safe_stats(self.bwd_pkt_lens)
        
        all_lens = self.fwd_pkt_lens + self.bwd_pkt_lens
        pkt_min, pkt_max, pkt_mean, pkt_std = safe_stats(all_lens)
        
        fwd_iat_min, fwd_iat_max, fwd_iat_mean, fwd_iat_std = safe_stats(self.fwd_iat)
        bwd_iat_min, bwd_iat_max, bwd_iat_mean, bwd_iat_std = safe_stats(self.bwd_iat)
        
        all_iats = self.fwd_iat + self.bwd_iat
        flow_iat_min, flow_iat_max, flow_iat_mean, flow_iat_std = safe_stats(all_iats)
        
        active_min, active_max, active_mean, active_std = safe_stats(self.active_times)
        idle_min, idle_max, idle_mean, idle_std = safe_stats(self.idle_times)
        
        # Build feature dictionary in EXACT order from feature_columns.pkl (71 features)
        # Protocol one-hot encoding: Protocol_0 (ICMP/Other), Protocol_6 (TCP), Protocol_17 (UDP)
        protocol = self.flow_key.protocol
        protocol_0 = 1.0 if protocol not in ['TCP', 'UDP'] else 0.0
        protocol_6 = 1.0 if protocol == 'TCP' else 0.0
        protocol_17 = 1.0 if protocol == 'UDP' else 0.0
        
        features = {
            'Dst Port': float(self.flow_key.dst_port),
            'Flow Duration': duration * 1000000,  # microseconds
            'Tot Fwd Pkts': float(total_fwd_pkts),
            'Tot Bwd Pkts': float(total_bwd_pkts),
            'TotLen Fwd Pkts': float(total_fwd_bytes),
            'TotLen Bwd Pkts': float(total_bwd_bytes),
            'Fwd Pkt Len Max': fwd_max,
            'Fwd Pkt Len Min': fwd_min,
            'Fwd Pkt Len Mean': fwd_mean,
            'Fwd Pkt Len Std': fwd_std,
            'Bwd Pkt Len Max': bwd_max,
            'Bwd Pkt Len Min': bwd_min,
            'Bwd Pkt Len Mean': bwd_mean,
            'Bwd Pkt Len Std': bwd_std,
            'Flow Byts/s': (total_fwd_bytes + total_bwd_bytes) / duration if duration > 0 else 0,
            'Flow Pkts/s': (total_fwd_pkts + total_bwd_pkts) / duration if duration > 0 else 0,
            'Flow IAT Mean': flow_iat_mean,
            'Flow IAT Std': flow_iat_std,
            'Flow IAT Max': flow_iat_max,
            'Flow IAT Min': flow_iat_min,
            'Fwd IAT Tot': sum(self.fwd_iat) if self.fwd_iat else 0,
            'Fwd IAT Mean': fwd_iat_mean,
            'Fwd IAT Std': fwd_iat_std,
            'Fwd IAT Max': fwd_iat_max,
            'Fwd IAT Min': fwd_iat_min,
            'Bwd IAT Tot': sum(self.bwd_iat) if self.bwd_iat else 0,
            'Bwd IAT Mean': bwd_iat_mean,
            'Bwd IAT Std': bwd_iat_std,
            'Bwd IAT Max': bwd_iat_max,
            'Bwd IAT Min': bwd_iat_min,
            'Fwd PSH Flags': 0,  # Would need to track separately
            'Fwd Header Len': total_fwd_pkts * 20,  # Approximate
            'Bwd Header Len': total_bwd_pkts * 20,
            'Fwd Pkts/s': total_fwd_pkts / duration if duration > 0 else 0,
            'Bwd Pkts/s': total_bwd_pkts / duration if duration > 0 else 0,
            'Pkt Len Min': pkt_min,
            'Pkt Len Max': pkt_max,
            'Pkt Len Mean': pkt_mean,
            'Pkt Len Std': pkt_std,
            'Pkt Len Var': pkt_std ** 2 if pkt_std > 0 else 0,
            'FIN Flag Cnt': float(self.fin_count),
            'SYN Flag Cnt': float(self.syn_count),
            'RST Flag Cnt': float(self.rst_count),
            'PSH Flag Cnt': float(self.psh_count),
            'ACK Flag Cnt': float(self.ack_count),
            'URG Flag Cnt': float(self.urg_count),
            'CWE Flag Count': float(self.cwr_count),
            'ECE Flag Cnt': float(self.ece_count),
            'Down/Up Ratio': total_bwd_bytes / total_fwd_bytes if total_fwd_bytes > 0 else 0,
            'Pkt Size Avg': pkt_mean,
            'Fwd Seg Size Avg': fwd_mean,
            'Bwd Seg Size Avg': bwd_mean,
            'Subflow Fwd Pkts': float(total_fwd_pkts),
            'Subflow Fwd Byts': float(total_fwd_bytes),
            'Subflow Bwd Pkts': float(total_bwd_pkts),
            'Subflow Bwd Byts': float(total_bwd_bytes),
            'Init Fwd Win Byts': 0,  # Would need TCP window tracking
            'Init Bwd Win Byts': 0,
            'Fwd Act Data Pkts': float(total_fwd_pkts),
            'Fwd Seg Size Min': fwd_min,
            'Active Mean': active_mean,
            'Active Std': active_std,
            'Active Max': active_max,
            'Active Min': active_min,
            'Idle Mean': idle_mean,
            'Idle Std': idle_std,
            'Idle Max': idle_max,
            'Idle Min': idle_min,
            'Protocol_0': protocol_0,
            'Protocol_6': protocol_6,
            'Protocol_17': protocol_17,
        }
        
        return features


class NetworkMonitor:
    """Real network traffic monitor using Scapy"""
    
    def __init__(self, callback: Optional[Callable] = None):
        self.running = False
        self.flows = {}
        self.callback = callback
        self.flow_timeout = 120  # seconds
        self.last_cleanup = time.time()
        self.packet_count = 0
        
        if not SCAPY_AVAILABLE:
            logger.error("Scapy not available - network monitoring disabled")
    
    def start(self):
        """Start network monitoring"""
        if not SCAPY_AVAILABLE:
            logger.error("Cannot start monitoring: Scapy not installed")
            return False
        
        if self.running:
            logger.warning("Network monitor already running")
            return False
        
        self.running = True
        logger.info("Network monitor started")
        return True
    
    def stop(self):
        """Stop network monitoring"""
        self.running = False
        self.flows.clear()
        logger.info("Network monitor stopped")
    
    def packet_handler(self, packet):
        """Handle captured packet"""
        if not self.running:
            return
        
        try:
            # Only process IP packets
            if IP not in packet:
                return
            
            ip_layer = packet[IP]
            timestamp = time.time()
            
            # Determine protocol
            if TCP in packet:
                proto = 'TCP'
                src_port = packet[TCP].sport
                dst_port = packet[TCP].dport
            elif UDP in packet:
                proto = 'UDP'
                src_port = packet[UDP].sport
                dst_port = packet[UDP].dport
            elif ICMP in packet:
                proto = 'ICMP'
                src_port = 0
                dst_port = 0
            else:
                return
            
            # Create flow key
            flow_key = FlowKey(
                ip_layer.src,
                ip_layer.dst,
                src_port,
                dst_port,
                proto
            )
            
            # Determine direction (forward if this is the initiating side)
            reverse_key = FlowKey(ip_layer.dst, ip_layer.src, dst_port, src_port, proto)
            
            if flow_key in self.flows:
                flow = self.flows[flow_key]
                is_forward = True
            elif reverse_key in self.flows:
                flow = self.flows[reverse_key]
                is_forward = False
            else:
                # New flow
                flow = NetworkFlow(flow_key)
                self.flows[flow_key] = flow
                is_forward = True
            
            # Add packet to flow
            flow.add_packet(packet, is_forward, timestamp)
            self.packet_count += 1
            
            # Cleanup old flows periodically
            if time.time() - self.last_cleanup > 10:
                self._cleanup_old_flows()
            
            # Check if flow is ready for analysis (minimum packets)
            if len(flow.fwd_packets) + len(flow.bwd_packets) >= 10:
                # Extract features and trigger callback
                if self.callback:
                    features = flow.extract_features()
                    self.callback(flow_key, features)
            
        except Exception as e:
            logger.error(f"Error processing packet: {e}")
    
    def _cleanup_old_flows(self):
        """Remove flows that haven't seen packets in a while"""
        current_time = time.time()
        to_remove = []
        
        for flow_key, flow in self.flows.items():
            if current_time - flow.last_packet_time > self.flow_timeout:
                to_remove.append(flow_key)
        
        for flow_key in to_remove:
            del self.flows[flow_key]
        
        self.last_cleanup = current_time
        
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old flows")
    
    def capture_packets(self, interface=None, count=0):
        """Start capturing packets (blocking)"""
        if not SCAPY_AVAILABLE:
            logger.error("Scapy not available")
            return
        
        logger.info(f"Starting packet capture (interface={interface or 'all'})")
        
        try:
            sniff(
                iface=interface,
                prn=self.packet_handler,
                store=False,
                count=count,
                stop_filter=lambda p: not self.running
            )
        except Exception as e:
            logger.error(f"Packet capture error: {e}")
            self.running = False
