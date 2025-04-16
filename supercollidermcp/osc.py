"""
OSC communication module for SuperCollider.

This module provides classes and functions for sending OSC messages to SuperCollider.
"""

import time
from pythonosc import udp_client

# Default SuperCollider settings
DEFAULT_SC_IP = "127.0.0.1"
DEFAULT_SC_PORT = 57110

class SuperColliderClient:
    """Client for communicating with SuperCollider via OSC."""
    
    def __init__(self, ip=DEFAULT_SC_IP, port=DEFAULT_SC_PORT):
        """
        Initialize a SuperCollider OSC client.
        
        Args:
            ip (str): The IP address of the SuperCollider server.
            port (int): The port of the SuperCollider server.
        """
        self.ip = ip
        self.port = port
        self.client = udp_client.SimpleUDPClient(ip, port)
    
    def send_message(self, address, args):
        """
        Send an OSC message to SuperCollider.
        
        Args:
            address (str): The OSC address pattern.
            args (list): A list of arguments to send with the message.
        """
        try:
            self.client.send_message(address, args)
            return True
        except Exception as e:
            print(f"Error sending OSC message: {e}")
            return False

    def create_synth(self, synth_name, node_id=1000, add_action=0, group_id=0, **kwargs):
        """
        Create a new synth node.
        
        Args:
            synth_name (str): The name of the synth definition.
            node_id (int): The ID to use for the new node.
            add_action (int): The add action (0=add to head, 1=add to tail, etc).
            group_id (int): The group ID to add the node to.
            **kwargs: Additional parameters to pass to the synth.
        """
        # Format args according to SuperCollider's /s_new protocol
        args = [synth_name, node_id, add_action, group_id]
        
        # Add any additional parameters
        for key, value in kwargs.items():
            args.append(key)
            args.append(value)
        
        return self.send_message("/s_new", args)
    
    def set_node_params(self, node_id, **kwargs):
        """
        Set parameters on an existing synth node.
        
        Args:
            node_id (int): The ID of the node to modify.
            **kwargs: Parameters to set on the node.
        """
        args = [node_id]
        
        # Add parameter pairs
        for key, value in kwargs.items():
            args.append(key)
            args.append(value)
        
        return self.send_message("/n_set", args)
    
    def free_node(self, node_id):
        """
        Free a synth node.
        
        Args:
            node_id (int): The ID of the node to free.
        """
        return self.send_message("/n_free", [node_id])
    
    def play_note(self, frequency=440, amplitude=0.5, duration=1.0, node_id=None):
        """
        Play a single note using a simple sine oscillator.
        
        Args:
            frequency (float): The frequency in Hz.
            amplitude (float): The amplitude (0-1).
            duration (float): The duration in seconds.
            node_id (int): The node ID to use (generated if None).
        """
        if node_id is None:
            # Generate a semi-random node ID to avoid conflicts
            node_id = int(time.time() * 1000) % 10000
            
        # Create the synth
        success = self.create_synth("default", node_id, 0, 0, freq=frequency, amp=amplitude)
        
        if success and duration > 0:
            # Wait and then free the node
            time.sleep(duration)
            self.free_node(node_id)
            
        return node_id

# Create a default client for convenience
default_client = SuperColliderClient()

# Export functions that use the default client
def send_message(address, args):
    """Send an OSC message using the default client."""
    return default_client.send_message(address, args)

def create_synth(synth_name, node_id=1000, add_action=0, group_id=0, **kwargs):
    """Create a new synth node using the default client."""
    return default_client.create_synth(synth_name, node_id, add_action, group_id, **kwargs)

def set_node_params(node_id, **kwargs):
    """Set parameters on an existing synth node using the default client."""
    return default_client.set_node_params(node_id, **kwargs)

def free_node(node_id):
    """Free a synth node using the default client."""
    return default_client.free_node(node_id)

def play_note(frequency=440, amplitude=0.5, duration=1.0, node_id=None):
    """Play a single note using the default client."""
    return default_client.play_note(frequency, amplitude, duration, node_id)
