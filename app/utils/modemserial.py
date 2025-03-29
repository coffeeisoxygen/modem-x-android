import logging
import re
import time

import serial
import serial.tools.list_ports


class SerialPort:
    def __init__(self, port):
        self.port = port
        self.connection = None
        self.logger = logging.getLogger(f"modem.{port}")
        self.response_history = []  # Add this line to store response history
        self.max_history = 10  # Maximum number of responses to keep

    def connect(self):
        try:
            self.connection = serial.Serial(self.port, baudrate=115200, timeout=1)
            self.logger.info(f"Connected to {self.port}")
        except Exception as e:
            self.logger.error(f"Failed to connect to {self.port}: {e}")

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.logger.info(f"Disconnected from {self.port}")

    def send_command(self, command, timeout=1):
        if not self.connection:
            self.logger.warning(f"Not connected to {self.port}")
            return None

        try:
            self.logger.debug(f"Sending command: {command}")
            self.connection.write((command + "\r\n").encode())
            time.sleep(timeout)
            response = self.connection.read(1024).decode()
            self.logger.debug(f"Raw response: {response}")

            # Store the command and response in history
            history_entry = f"CMD: {command}\nRESP: {response.strip()}"
            self.response_history.append(history_entry)

            # Keep only the last max_history entries
            if len(self.response_history) > self.max_history:
                self.response_history = self.response_history[-self.max_history :]

            return response
        except Exception as e:
            error_msg = f"Error sending command to {self.port}: {e}"
            self.logger.error(error_msg)
            self.response_history.append(f"CMD: {command}\nERROR: {str(e)}")
            return None

    def parse_response(self, response, pattern=None):
        """Parse the AT command response to extract meaningful data"""
        if not response:
            return None

        # Remove command echo
        lines = response.strip().split("\r\n")
        # Remove empty lines and OK/ERROR responses
        lines = [line for line in lines if line and line not in ["OK", "ERROR"]]

        if not lines:
            return None

        # If a specific pattern is provided, extract using regex
        if pattern:
            for line in lines:
                match = re.search(pattern, line)
                if match:
                    return match.group(1)

        # Return the most likely data line
        for line in lines:
            if not line.startswith("AT"):
                return line

        return lines[0] if lines else None

    def get_imei(self):
        response = self.send_command("AT+GSN")
        return self.parse_response(response, r"(\d{15})")

    def get_iccid(self):
        response = self.send_command("AT+CCID")
        return self.parse_response(response, r"CCID:\s*(\d+)")

    def get_signal_strength(self):
        response = self.send_command("AT+CSQ")
        match = None
        if response:
            match = re.search(r"CSQ:\s*(\d+),", response)

        if match:
            signal = int(match.group(1))
            # Convert to percentage (0-31 range)
            if signal == 99:  # 99 means no signal
                return "No signal"
            percentage = min(100, int(signal * 100 / 31))
            return f"{percentage}%"
        return self.parse_response(response)

    def get_number(self):
        # Directly use the USSD command to retrieve the number
        response = self.send_command('AT+CUSD=1,"*185#",15', timeout=5)
        return self.parse_response(response)

    def get_response_history(self):
        """Get the history of AT command responses."""
        if not self.response_history:
            return "No command history"
        return "\n".join(self.response_history)


class ModemPool:
    def __init__(self):
        self.modems = []
        self.logger = logging.getLogger("modem.pool")

    def detect_modems(self):
        self.logger.info("Detecting modems...")
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.logger.debug(f"Found port: {port.device} - {port.description}")
            if "USB" in port.description:
                modem = SerialPort(port.device)
                self.modems.append(modem)
        self.logger.info(f"Detected {len(self.modems)} modem(s)")

    def list_modems(self):
        for idx, modem in enumerate(self.modems):
            self.logger.info(f"[{idx + 1}] Port: {modem.port}")

    def refresh(self):
        self.logger.info("Refreshing modem pool")
        # Close existing connections
        for modem in self.modems:
            modem.disconnect()
        self.modems = []
        self.detect_modems()

    def execute_command(self, command, all_ports=True):
        results = {}
        self.logger.info(
            f"Executing command: {command} on {'all ports' if all_ports else 'first port'}"
        )
        if all_ports:
            for modem in self.modems:
                results[modem.port] = modem.send_command(command)
        else:
            if self.modems:
                results[self.modems[0].port] = self.modems[0].send_command(command)
        return results
