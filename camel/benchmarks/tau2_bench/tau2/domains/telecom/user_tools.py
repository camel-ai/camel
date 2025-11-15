from typing import Any, Dict, Literal, Optional, Tuple, Union

from tau2.domains.telecom.user_data_model import (
    APNNames,
    APNSettings,
    AppPermissions,
    AppStatus,
    MockPhoneAttributes,
    NetworkModePreference,
    NetworkStatus,
    NetworkTechnology,
    PaymentRequest,
    PerformanceLevel,
    SignalStrength,
    SimStatus,
    TelecomUserDB,
    UserSurroundings,
    VpnDetails,
)
from tau2.environment.toolkit import ToolKitBase, ToolType, is_tool


class TelecomUserTools(ToolKitBase):
    """
    Provides methods to simulate user actions and agent instructions
    on a MockPhoneAttributes instance.
    """

    db: TelecomUserDB

    network_mode_preference: NetworkModePreference = (
        NetworkModePreference.FOUR_G_5G_PREFERRED
    )

    default_vpn_details: VpnDetails = VpnDetails(
        server_address="192.168.1.1",
        protocol="OpenVPN",
        server_performance=PerformanceLevel.EXCELLENT,
    )

    def __init__(
        self,
        db: TelecomUserDB,
    ):
        """
        Initializes
        """
        super().__init__(db)

    # --- Properties ---
    @property
    def device(self) -> MockPhoneAttributes:
        """Returns the full current state of the device attributes."""
        return self.db.device

    @property
    def surroundings(self) -> UserSurroundings:
        """Returns the full current state of the surroundings attributes."""
        return self.db.surroundings

    # --- User Info ---
    def set_user_info(self, name: str, phone_number: str):
        """
        Sets the user's name and phone number.
        """
        self.db.surroundings.name = name
        self.db.surroundings.phone_number = phone_number

    def set_user_location(self, abroad: bool):
        """
        Sets the user's location to abroad or not.
        """
        self.db.surroundings.is_abroad = abroad

    # --- Status Bar ---
    @is_tool(ToolType.READ)
    def check_status_bar(self) -> str:
        """Shows what icons are currently visible in your phone's status bar (the area at the top of the screen). Displays network signal strength, mobile data status (enabled, disabled, data saver), Wi-Fi status, and battery level."""
        return f"Status Bar: {self._check_status_bar()}"

    def _check_status_bar(self) -> str:
        """
        Returns a string representation of the phone's status bar with basic indicators.
        Shows network signal, data connection type, wifi status, airplane mode, and battery level.
        """
        device = self.device

        # Build the status indicators
        indicators = []

        # Airplane mode (takes precedence)
        if device.airplane_mode:
            indicators.append("✈️ Airplane Mode")
        else:
            # Signal strength indicator
            signal_map = {
                SignalStrength.NONE: "📵 No Signal",
                SignalStrength.POOR: "📶¹ Poor",
                SignalStrength.FAIR: "📶² Fair",
                SignalStrength.GOOD: "📶³ Good",
                SignalStrength.EXCELLENT: "📶⁴ Excellent",
            }
            indicators.append(
                signal_map.get(device.network_signal_strength, "📵 No Signal")
            )

            # Network technology
            if device.network_technology_connected != NetworkTechnology.NONE:
                indicators.append(device.network_technology_connected.value)

            # Data enabled indicator
            if (
                device.data_enabled
                and device.network_technology_connected != NetworkTechnology.NONE
            ):
                indicators.append("📱 Data Enabled")
                if device.data_saver_mode:
                    indicators.append("🔽 Data Saver")
            else:
                indicators.append("📵 Data Disabled")

        # WiFi indicator
        if device.wifi_enabled and device.wifi_connected:
            if device.wifi_ssid:
                indicators.append(f"📡 Connected to {device.wifi_ssid}")
            else:
                indicators.append("📡 Enabled")

        # TODO: Should VPN be shown as connected if there is no data?
        # VPN indicator
        if device.vpn_connected:
            indicators.append("🔒 VPN Connected")

        # Battery level
        battery_level = device.battery_level
        indicators.append(f"🔋 {battery_level}%")

        # Combine all indicators
        return " | ".join(indicators)

    # --- Network (General) ---
    @is_tool(ToolType.READ)
    def check_network_status(self) -> str:
        """Checks your phone's connection status to cellular networks and Wi-Fi. Shows airplane mode status, signal strength, network type, whether mobile data is enabled, and whether data roaming is enabled."""
        status = self._check_network_status()
        lines = [
            f"Airplane Mode: {'ON' if status['airplane_mode'] else 'OFF'}",
            f"SIM Card Status: {status['sim_status'].value}",
            f"Cellular Connection: {status['connection_status'].value}",
            f"Cellular Signal: {status['signal_strength'].value}",
            f"Cellular Network Type: {status['network_technology'].value}",
            f"Mobile Data Enabled: {'Yes' if status['mobile_data_enabled'] else 'No'}",
            f"Data Roaming Enabled: {'Yes' if status['data_roaming_enabled'] else 'No'}",
            f"Wi-Fi Radio: {'ON' if status['wifi_enabled'] else 'OFF'}",
            f"Wi-Fi Connected: {'Yes' if status['wifi_connected'] else 'No'}",
        ]
        if status["wifi_connected"]:
            lines.append(f"Connected Wi-Fi Network: {status['wifi_ssid']}")
        return "\n".join(lines)

    def _check_network_status(self) -> Dict[str, Any]:
        """
        Returns a dictionary summarizing key network-related statuses.
        Useful for quick diagnosis by an agent.
        """
        return {
            "airplane_mode": self.device.airplane_mode,
            "sim_status": self._check_sim_status(),
            "connection_status": self.device.network_connection_status,
            "signal_strength": self.device.network_signal_strength,
            "network_technology": self.device.network_technology_connected,
            "mobile_data_enabled": self.device.data_enabled,
            "data_roaming_enabled": self.device.roaming_enabled,
            "wifi_enabled": self.device.wifi_enabled,
            "wifi_connected": self.device.wifi_connected,
            "wifi_ssid": self.device.wifi_ssid,
        }

    @is_tool(ToolType.READ)
    def check_network_mode_preference(self) -> str:
        """Shows the current network mode preference."""
        return f"Network Mode Preference: {self._check_network_mode_preference().value}"

    def _check_network_mode_preference(self) -> NetworkModePreference:
        """Returns the current network mode preference."""
        return self.device.network_mode_preference

    @is_tool(ToolType.WRITE)
    def set_network_mode_preference(
        self, mode: Union[NetworkModePreference, str]
    ) -> str:
        """Changes the type of cellular network your phone prefers to connect to (e.g., 5G, LTE/4G, 3G). Higher-speed networks (LTE/5G) provide faster data but may use more battery."""
        valid_mode = self._set_network_mode_preference(mode)
        if valid_mode is None:
            return f"Failed to set network mode: '{mode}' is not a valid option. Please use one of: {', '.join([m.value for m in NetworkModePreference])}\nStatus Bar: {self._check_status_bar()}"
        status_update = f"Preferred Network Mode set to: {valid_mode.value}"
        return f"{status_update}\nStatus Bar: {self._check_status_bar()}"

    def _set_network_mode_preference(
        self, mode: Union[NetworkModePreference, str]
    ) -> Optional[NetworkModePreference]:
        """Sets the preferred network mode.
        This will trigger a network search.
        """
        try:
            if isinstance(mode, str):
                mode = NetworkModePreference(mode)
            self.device.network_mode_preference = mode
            self.simulate_network_search()
            return mode
        except ValueError:
            return None

    def _get_mobile_data_working(self) -> bool:
        """Returns True if mobile data is working, False otherwise.

        The mobile data not working when any of the following are true:
        - Airplane mode is on
        - No signal
        - No service
        - Data Roaming is not allowed and the user is abroad
        - Data is not enabled
        - Data usage is exceeded
        """
        if (
            self.device.airplane_mode
            or self.device.network_signal_strength == SignalStrength.NONE
        ):
            return False

        if self.device.network_connection_status == NetworkStatus.NO_SERVICE:
            return False

        if self.surroundings.is_abroad:
            if not self.device.roaming_enabled or not self.surroundings.roaming_allowed:
                return False

        if not self.device.data_enabled:
            return False

        if self.surroundings.mobile_data_usage_exceeded:
            return False

        return True

    @is_tool(ToolType.READ)
    def run_speed_test(self) -> str:
        """Measures your current internet connection speed (download speed). Provides information about connection quality and what activities it can support."""
        speed_mbps, description = self._run_speed_test()

        if speed_mbps is None:
            return f"Speed test failed: {description or 'Could not determine speed'}."

        # Provide more context based on description
        if description == "Very Poor":
            advice = "Connection is very slow. Basic web browsing might be difficult."
        elif description == "Poor":
            advice = (
                "Connection is slow. Web browsing may be sluggish, streaming difficult."
            )
        elif description == "Fair":
            advice = "Connection is okay for web browsing and some standard definition streaming."
        elif description == "Good":
            advice = "Connection is good for most activities, including HD streaming."
        elif description == "Excellent":
            advice = "Connection is very fast."
        else:
            advice = ""

        return f"Speed Test Result: {speed_mbps:.2f} Mbps ({description}). {advice}"

    def _run_speed_test(self) -> Tuple[Optional[float], Optional[str]]:
        """
        Simulates running a speed test for mobile data based on current network conditions.
        Returns a tuple: (speed_mbps, description).

        The speed calculation takes into account multiple factors:
        1. Base Conditions:
           - Returns None if mobile data is not working
           - Reduces speed by 90% if VPN is connected with poor performance
           - Reduces speed by 50% if data saver mode is enabled

        2. Network Technology:
           - 2G: 0.1-0.4 Mbps
           - 3G: 1.0-5.0 Mbps
           - 4G: 10.0-50.0 Mbps
           - LTE: 15.0-100.0 Mbps
           - 5G: 50.0-500.0 Mbps

        3. Signal Strength Multipliers:
           - Poor: 20% of potential speed
           - Fair: 50% of potential speed
           - Good: 80% of potential speed
           - Excellent: 100% of potential speed

        The final speed is calculated as:
        (min_speed + max_speed)/2 * signal_factor * base_speed_factor

        Speed descriptions are categorized as:
        - < 1 Mbps: Very Poor
        - 1-5 Mbps: Poor
        - 5-25 Mbps: Fair
        - 25-100 Mbps: Good
        - > 100 Mbps: Excellent
        """

        if not self._get_mobile_data_working():
            return None, "No Connection"

        if (
            self.device.vpn_connected
            and self.device.vpn_details
            and self.device.vpn_details.server_performance == PerformanceLevel.POOR
        ):
            # Reduce potential speed significantly due to VPN
            base_speed_factor = 0.1
        else:
            base_speed_factor = 1.0

        if self.device.data_saver_mode:
            base_speed_factor *= 0.2  # Reduce speed due to data saver

        # Base speed ranges based on technology (adjust as needed)
        tech_speed_map = {
            NetworkTechnology.TWO_G: (0.1, 0.4),
            NetworkTechnology.THREE_G: (1.0, 5.0),
            NetworkTechnology.FOUR_G: (10.0, 100.0),
            NetworkTechnology.FIVE_G: (50.0, 500.0),
            NetworkTechnology.NONE: (0.0, 0.0),
        }
        min_speed, max_speed = tech_speed_map.get(
            self.device.network_technology_connected, (0.0, 0.0)
        )

        # Adjust speed based on signal strength
        signal_factor_map = {
            SignalStrength.POOR: 0.2,
            SignalStrength.FAIR: 0.5,
            SignalStrength.GOOD: 0.8,
            SignalStrength.EXCELLENT: 1.0,
            SignalStrength.NONE: 0.0,
        }
        signal_factor = signal_factor_map.get(self.device.network_signal_strength, 0.0)

        # Calculate simulated speed
        simulated_speed = (
            (min_speed + max_speed) / 2.0 * signal_factor * base_speed_factor
        )
        simulated_speed = round(simulated_speed, 2)

        # Determine description
        desc = "Unknown"
        if simulated_speed < 1:
            desc = "Very Poor"
        elif simulated_speed < 5:
            desc = "Poor"
        elif simulated_speed < 25:
            desc = "Fair"
        elif simulated_speed < 100:
            desc = "Good"
        else:
            desc = "Excellent"
        return simulated_speed, desc

    # --- Airplane Mode ---
    @is_tool(ToolType.WRITE)
    def toggle_airplane_mode(self) -> str:
        """Toggles Airplane Mode ON or OFF. When ON, it disconnects all wireless communications including cellular, Wi-Fi, and Bluetooth.
        Returns the new state of airplane_mode.
        """
        new_state = self._toggle_airplane_mode()
        status_update = f"Airplane Mode is now {'ON' if new_state else 'OFF'}."
        return f"{status_update}\nStatus Bar: {self._check_status_bar()}"

    def _toggle_airplane_mode(self) -> bool:
        """
        Toggles Airplane Mode ON or OFF. If turning OFF, simulates a network search.
        Returns the new state of airplane_mode.
        """
        current_airplane_mode_on = self.device.airplane_mode
        self.device.airplane_mode = not current_airplane_mode_on

        if current_airplane_mode_on:  # Turning OFF
            self.device.network_connection_status = NetworkStatus.SEARCHING

            if self.device.wifi_enabled:
                self.device.wifi_connected = False
                self.device.wifi_ssid = None
                self.device.wifi_signal_strength = SignalStrength.NONE

        elif not current_airplane_mode_on:  # Turning ON
            self.device.wifi_connected = False
            self.device.wifi_ssid = None
            self.device.wifi_signal_strength = SignalStrength.NONE
            # Disconnect VPN
            if self.device.vpn_connected:
                self._disconnect_vpn()

        self.simulate_network_search()
        return self.device.airplane_mode

    def turn_airplane_mode_on(self) -> str:
        """Turns Airplane Mode ON."""
        new_state = self._toggle_airplane_mode()
        if not new_state:
            new_state = self._toggle_airplane_mode()
        return "Airplane Mode is now ON."

    def turn_airplane_mode_off(self) -> str:
        """Turns Airplane Mode OFF."""
        new_state = self._toggle_airplane_mode()
        if new_state:
            new_state = self._toggle_airplane_mode()
        return "Airplane Mode is now OFF."

    # --- SIM Card ---
    @is_tool(ToolType.READ)
    def check_sim_status(self) -> str:
        """Checks if your SIM card is working correctly and displays its current status. Shows if the SIM is active, missing, or locked with a PIN or PUK code."""
        status = self._check_sim_status()
        status_map = {
            SimStatus.ACTIVE: "Your SIM card is active and working.",
            SimStatus.MISSING: "No SIM card detected in the phone.",
            SimStatus.LOCKED_PIN: "The SIM card is locked with a PIN code.",
            SimStatus.LOCKED_PUK: "The SIM card is locked with a PUK code.",
        }
        return status_map.get(status, f"Unknown SIM status: {status.value}")

    def _check_sim_status(self) -> SimStatus:
        """Returns the current status of the SIM card."""
        if self.device.sim_card_missing:
            return SimStatus.MISSING
        return self.device.sim_card_status

    @is_tool(ToolType.WRITE)
    def reseat_sim_card(self) -> str:
        """Simulates removing and reinserting your SIM card. This can help resolve recognition issues."""
        status_update = self._reseat_sim_card()
        return f"{status_update}\nStatus Bar: {self._check_status_bar()}"

    def _reseat_sim_card(self) -> str:
        """Re-seats the SIM card by removing and re-inserting it."""
        self.device.sim_card_missing = False
        self.simulate_network_search()
        assert not self.device.sim_card_missing
        assert self._check_sim_status() != SimStatus.MISSING
        return "SIM card re-seated successfully."

    def unseat_sim_card(self) -> str:
        """Un-seats the SIM card by removing it. This is fixed by calling reseat_sim_card()."""
        self.device.sim_card_missing = True
        self.simulate_network_search()
        assert self.device.sim_card_missing
        assert self._check_sim_status() == SimStatus.MISSING
        return "SIM card un-seated successfully."

    def lock_sim_card(self, mode: Literal["pin", "puk"]) -> str:
        """Locks the SIM card by setting the PIN. This cannot be fixed by calling a tool."""
        if mode == "pin":
            self.device.sim_card_status = SimStatus.LOCKED_PIN
        elif mode == "puk":
            self.device.sim_card_status = SimStatus.LOCKED_PUK
        self.simulate_network_search()
        if mode == "pin":
            assert self.device.sim_card_status == SimStatus.LOCKED_PIN
        elif mode == "puk":
            assert self.device.sim_card_status == SimStatus.LOCKED_PUK
        return f"SIM card locked successfully in {mode} mode."

    # --- Mobile Data & Roaming ---
    @is_tool(ToolType.WRITE)
    def toggle_data(self) -> str:
        """Toggles your phone's mobile data connection ON or OFF. Controls whether your phone can use cellular data for internet access when Wi-Fi is unavailable.
        Returns the new data connection status.
        """
        new_state = self._toggle_data()
        status_update = f"Mobile Data is now {'ON' if new_state else 'OFF'}."
        return f"{status_update}\nStatus Bar: {self._check_status_bar()}"

    def _toggle_data(self) -> bool:
        """Toggles the master Mobile Data switch. Returns the new state."""
        new_state = not self.device.data_enabled
        self.device.data_enabled = new_state
        self.simulate_network_search()
        return new_state

    def turn_data_on(self) -> str:
        """Turns Data ON."""
        self.device.data_enabled = True
        return "Data connection restored."

    def turn_data_off(self) -> str:
        """Turns Data OFF."""
        new_state = self._toggle_data()
        if new_state:
            new_state = self._toggle_data()
        return "Data connection broken."

    @is_tool(ToolType.WRITE)
    def toggle_roaming(self) -> str:
        """Toggles Data Roaming ON or OFF. When ON, your phone can use data networks in areas outside your carrier's coverage.
        Returns the new data roaming status.
        """
        new_state = self._toggle_roaming()
        status_update = f"Data Roaming is now {'ON' if new_state else 'OFF'}."
        return f"{status_update}\nStatus Bar: {self._check_status_bar()}"

    def _toggle_roaming(self) -> bool:
        """Toggles the Data Roaming setting. Returns the new state."""
        new_state = not self.device.roaming_enabled
        self.device.roaming_enabled = new_state
        self.simulate_network_search()
        return new_state

    def turn_roaming_on(self) -> str:
        """Turns Data Roaming ON."""
        new_state = self._toggle_roaming()
        if not new_state:
            new_state = self._toggle_roaming()
        return "Data Roaming is now ON."

    def turn_roaming_off(self) -> str:
        """Turns Data Roaming OFF."""
        new_state = self._toggle_roaming()
        if new_state:
            new_state = self._toggle_roaming()
        return "Data Roaming is now OFF."

    @is_tool(ToolType.READ)
    def check_data_restriction_status(self) -> str:
        """Checks if your phone has any data-limiting features active. Shows if Data Saver mode is on."""
        status = self._check_data_restriction_status()
        lines = []
        if status["data_saver_mode"]:
            lines.append("Data Saver mode is ON (limits data usage).")
        else:
            lines.append("Data Saver mode is OFF.")
        return "\n".join(lines)

    def _check_data_restriction_status(self) -> Dict[str, bool]:
        """Checks global data saving/restriction settings."""
        return {
            "data_saver_mode": self.device.data_saver_mode,
        }

    @is_tool(ToolType.WRITE)
    def toggle_data_saver_mode(self) -> str:
        """Toggles Data Saver mode ON or OFF. When ON, it reduces data usage, which may affect data speed.
        Returns the new data saver mode status.
        """
        new_state = self._toggle_data_saver_mode()
        status_update = f"Data Saver Mode is now {'ON' if new_state else 'OFF'}."
        return f"{status_update}\nStatus Bar: {self._check_status_bar()}"

    def _toggle_data_saver_mode(self) -> bool:
        """Toggles Data Saver mode. Returns the new state."""
        new_state = not self.device.data_saver_mode
        self.device.data_saver_mode = new_state
        return new_state

    def turn_data_saver_mode_on(self) -> str:
        """Turns Data Saver mode ON."""
        new_state = self._toggle_data_saver_mode()
        if not new_state:
            new_state = self._toggle_data_saver_mode()
        return "Data Saver Mode is now ON."

    def turn_data_saver_mode_off(self) -> str:
        """Turns Data Saver mode OFF."""
        new_state = self._toggle_data_saver_mode()
        if new_state:
            new_state = self._toggle_data_saver_mode()
        return "Data Saver Mode is now OFF."

    # --- APN Settings ---
    @is_tool(ToolType.READ)
    def check_apn_settings(self) -> str:
        """Checks the technical APN settings your phone uses to connect to your carrier's mobile data network. Shows current APN name and MMSC URL for picture messaging."""
        settings = self._check_apn_settings()
        # Only show a few key, potentially relevant settings for a non-tech user
        apn_name = settings.apn_name.value or "Not Set"
        mmsc_url = settings.mmsc_url or "Not Set"
        return f"Current APN Name: {apn_name}\nMMSC URL (for picture messages): {mmsc_url}\n(These are technical settings, usually best left unchanged.)"

    def _check_apn_settings(self) -> APNSettings:
        """Returns the currently active APN settings."""
        # Return a copy to prevent accidental modification outside of setters
        return self.device.active_apn_settings.model_copy(deep=True)

    @is_tool(ToolType.WRITE)
    def set_apn_settings(self, apn_settings: Union[APNSettings, dict]) -> str:
        """Sets the APN settings for the phone."""
        if isinstance(apn_settings, dict):
            apn_settings = APNSettings(**apn_settings)
        status_update = self._set_apn_settings(apn_settings)
        self.simulate_network_search()
        return f"{status_update}\nStatus Bar: {self._check_status_bar()}"

    def _set_apn_settings(self, apn_settings: APNSettings) -> str:
        """Sets the APN settings for the phone."""
        self.device.active_apn_settings = apn_settings
        return f"APN settings set to: {apn_settings.apn_name.value}"

    @is_tool(ToolType.WRITE)
    def reset_apn_settings(self) -> str:
        """Resets your APN settings to the default settings."""
        apn_status = self._reset_apn_settings()
        self.simulate_network_search()
        return f"{apn_status}\nStatus Bar: {self._check_status_bar()}"

    def _reset_apn_settings(self):
        """Resets your APN settings to the default settings. This will be applied at the next reboot."""
        self.device.active_apn_settings.reset_at_reboot = True
        return f"APN settings will reset at reboot."

    def break_apn_settings(self) -> str:
        """Breaks the APN settings. This is fixed by calling reset_apn_settings()."""
        self.device.active_apn_settings.apn_name = APNNames.BROKEN
        self.simulate_network_search()
        assert self.device.network_connection_status == NetworkStatus.NO_SERVICE
        return "APN settings broken. Please call reset_apn_settings() to fix."

    def break_apn_mms_setting(self) -> str:
        """Breaks the APN MMS setting. This is fixed by calling reset_apn_settings()."""
        self.device.active_apn_settings.mmsc_url = None
        assert not self._can_send_mms()
        return "APN MMS setting broken. Please call reset_apn_settings() to fix."

    # --- Wi-Fi ---
    @is_tool(ToolType.READ)
    def check_wifi_status(self) -> str:
        """Checks your Wi-Fi connection status. Shows if Wi-Fi is turned on, which network you're connected to (if any), and the signal strength."""
        status = self._check_wifi_status()
        if not status["enabled"]:
            return "Wi-Fi is turned OFF."
        if status["connected"]:
            return f"Wi-Fi is ON and connected to '{status['ssid']}'. Signal strength: {status['signal_strength'].value}."
        else:
            return "Wi-Fi is ON but not connected to any network."

    def _check_wifi_status(self) -> Dict[str, Any]:
        """Returns the current Wi-Fi status details."""
        return {
            "enabled": self.device.wifi_enabled,
            "connected": self.device.wifi_connected,
            "ssid": self.device.wifi_ssid,
            "signal_strength": self.device.wifi_signal_strength,
        }

    @is_tool(ToolType.WRITE)
    def toggle_wifi(self) -> str:
        """Toggles your phone's Wi-Fi radio ON or OFF. Controls whether your phone can discover and connect to wireless networks for internet access.
        Returns the new Wi-Fi status.
        """
        new_state = self._toggle_wifi()
        if new_state is None:
            return f"Cannot change Wi-Fi settings while Airplane Mode is ON.\nStatus Bar: {self._check_status_bar()}"
        status_update = f"Wi-Fi is now {'ON' if new_state else 'OFF'}."
        return f"{status_update}\nStatus Bar: {self._check_status_bar()}"

    def _toggle_wifi(self) -> Optional[bool]:
        """Toggles the Wi-Fi radio. Returns the new state."""
        if self.device.airplane_mode:
            return None

        new_state = not self.device.wifi_enabled
        self.device.wifi_enabled = new_state
        if not new_state:  # Turning Wi-Fi OFF
            self.device.wifi_connected = False
            self.device.wifi_ssid = None
            self.device.wifi_signal_strength = SignalStrength.NONE
        return new_state

    # --- Wi-Fi Calling ---
    @is_tool(ToolType.READ)
    def check_wifi_calling_status(self) -> str:
        """Checks if Wi-Fi Calling is enabled on your device. This feature allows you to make and receive calls over a Wi-Fi network instead of using the cellular network."""
        status = self._check_wifi_calling_status()
        enabled_str = "ON" if status["enabled"] else "OFF"
        # MMS preference might be too technical, keep it simple
        return f"Wi-Fi Calling is currently turned {enabled_str}."

    def _check_wifi_calling_status(self) -> Dict[str, bool]:
        """Returns the status of Wi-Fi Calling settings."""
        return {
            "enabled": self.device.wifi_calling_enabled,
            "mms_enabled": self.device.wifi_calling_mms_over_wifi,
        }

    @is_tool(ToolType.WRITE)
    def toggle_wifi_calling(self) -> str:
        """Toggles Wi-Fi Calling ON or OFF. This feature allows you to make and receive calls over Wi-Fi instead of the cellular network, which can help in areas with weak cellular signal.
        Returns the new Wi-Fi Calling status.
        """
        new_state = self._toggle_wifi_calling()
        status_update = f"Wi-Fi Calling is now {'ON' if new_state else 'OFF'}."
        return f"{status_update}\nStatus Bar: {self._check_status_bar()}"

    def _toggle_wifi_calling(self) -> bool:
        """Toggles the Wi-Fi Calling setting. Returns the new state."""
        new_state = not self.device.wifi_calling_enabled
        self.device.wifi_calling_enabled = new_state
        return new_state

    def set_wifi_calling(
        self, enabled: bool, mms_over_wifi: Optional[bool] = None
    ) -> str:
        """Set the Wi-Fi Calling setting. Set MMS over WIFI accordingly if provided."""
        if self.device.wifi_calling_enabled != enabled:
            self._toggle_wifi_calling()
        msg = f"Wi-Fi Calling is now {'ON' if enabled else 'OFF'}."
        if mms_over_wifi is not None:
            self.device.wifi_calling_mms_over_wifi = mms_over_wifi
            msg += f"\nMMS over Wi-Fi is now {'ON' if mms_over_wifi else 'OFF'}."
        return msg

    # --- VPN ---
    @is_tool(ToolType.READ)
    def check_vpn_status(self) -> str:
        """Checks if you're using a VPN (Virtual Private Network) connection. Shows if a VPN is active, connected, and displays any available connection details."""
        status = self._check_vpn_status()
        if status["connected"]:
            details = status["details"]
            if details:
                return f"VPN is ON and connected. Details: {details}"
            else:
                return "VPN is ON and connected (no specific details available)."
        elif status["enabled_setting"]:
            return "VPN is turned ON in settings, but currently not connected."
        else:
            return "VPN is turned OFF."

    def _check_vpn_status(self) -> Dict[str, Any]:
        """Returns the current VPN status and details if connected."""
        return {
            "enabled_setting": self.device.vpn_enabled_setting,
            "connected": self.device.vpn_connected,
            "details": (
                self.device.vpn_details.model_dump()
                if self.device.vpn_details and self.device.vpn_connected
                else None
            ),
        }

    @is_tool(ToolType.WRITE)
    def connect_vpn(self) -> str:
        """Connects to your VPN (Virtual Private Network)."""
        connected = self._connect_vpn()
        if connected is None:
            return "VPN already connected."
        status_update = (
            "VPN connected successfully."
            if connected
            else "No VPN connection to connect."
        )
        return f"{status_update}\nStatus Bar: {self._check_status_bar()}"

    def _connect_vpn(self) -> Optional[bool]:
        """Connects to a VPN (Virtual Private Network).
        This will set the VPN connection to the default details.
        """
        if self.device.vpn_connected:
            return None
        self.device.vpn_connected = True
        self.device.vpn_details = self.default_vpn_details
        return True

    @is_tool(ToolType.WRITE)
    def disconnect_vpn(self) -> str:
        """Disconnects any active VPN (Virtual Private Network) connection. Stops routing your internet traffic through a VPN server, which might affect connection speed or access to content."""
        disconnected = self._disconnect_vpn()
        status_update = (
            "VPN disconnected successfully."
            if disconnected
            else "No active VPN connection to disconnect."
        )
        return f"{status_update}\nStatus Bar: {self._check_status_bar()}"

    def _disconnect_vpn(self) -> bool:
        """Disconnects any active VPN connection."""
        if not self.device.vpn_connected:
            return False
        self.device.vpn_connected = False
        self.device.vpn_details = None
        return True

    def break_vpn(self) -> str:
        """Breaks the VPN connection. Results in a slow mobile data."""
        self.connect_vpn()
        self.device.vpn_details.server_performance = PerformanceLevel.POOR
        return "VPN connection broken."

    # --- Applications ---
    @is_tool(ToolType.READ)
    def check_installed_apps(self) -> str:
        """Returns the name of all installed apps on the phone."""
        app_names = ", ".join(self._check_installed_apps())
        return f"The following apps are installed on the phone: {app_names}"

    def _check_installed_apps(self) -> list[str]:
        """Returns a list of all app names installed on the phone."""
        return list(self.device.app_statuses.keys())

    @is_tool(ToolType.READ)
    def check_app_status(self, app_name: str) -> str:
        """Checks detailed information about a specific app. Shows its permissions and background data usage settings."""
        app_status = self._check_app_status(app_name)
        if app_status is None:
            return f"App '{app_name}' not found on this phone."

        lines = [f"Status for App: {app_name}"]

        # Permissions Summary (using the logic from get_app_permissions)
        allowed_perms = [
            name.replace("_", " ").lower()  # change from capitalize to lowercase
            for name, allowed in app_status.permissions.model_dump().items()
            if allowed
        ]
        if not allowed_perms:
            lines.append(" - Permissions: None granted.")
        else:
            lines.append(" - Permissions Granted:")
            for perm in allowed_perms:
                lines.append(f"   - {perm}")

        return "\n".join(lines)

    def _check_app_status(self, app_name: str) -> Optional[AppStatus]:
        """Gets the full status object for a specific app."""
        app_status = self.device.app_statuses.get(app_name)
        if app_status:
            return app_status.model_copy(deep=True)
        return None

    @is_tool(ToolType.READ)
    def check_app_permissions(self, app_name: str) -> str:
        """Checks what permissions a specific app currently has. Shows if the app has access to features like storage, camera, location, etc."""
        permissions = self._check_app_permissions(app_name)
        if permissions is None:
            # Check if app exists at all
            return f"App '{app_name}' not found on this phone."
        allowed_perms = [
            name.replace("_", " ").lower()  # change from capitalize to lowercase
            for name, allowed in permissions.model_dump().items()
            if allowed
        ]

        if not allowed_perms:
            return f"App '{app_name}' currently has no permissions granted."
        else:
            return f"App '{app_name}' has permission for: {', '.join(allowed_perms)}."

    def _check_app_permissions(self, app_name: str) -> Optional[AppPermissions]:
        """Gets the permissions status for a specific app."""
        app_status = self.device.app_statuses.get(app_name)
        if app_status:
            return app_status.permissions
        return None

    @is_tool(ToolType.WRITE)
    def grant_app_permission(self, app_name: str, permission: str) -> str:
        """Gives a specific permission to an app (like access to storage, camera, or location). Required for some app functions to work properly.

        Args:
            app_name: The name of the app to grant the permission to.
            permission: The permission to grant, should be lowercase.
        """
        success, message = self._grant_app_permission(app_name, permission)
        result = "Success. " if success else "Error. "
        return f"{result}{message}\nStatus Bar: {self._check_status_bar()}"

    def _grant_app_permission(self, app_name: str, permission: str) -> Tuple[bool, str]:
        """Grants a specific permission to an app."""
        app_status = self.device.app_statuses.get(app_name)
        permission = permission.lower()
        if app_status:
            available_permissions = list(app_status.permissions.model_dump().keys())
            if permission not in available_permissions:
                return (
                    False,
                    f"Permission '{permission}' not tracked for app '{app_name}', available permissions: {available_permissions}",
                )
            setattr(app_status.permissions, permission, True)
            return True, f"Permission '{permission}' granted to app '{app_name}'."
        else:
            # Already checked in public method
            return False, f"App '{app_name}' not found. Cannot grant permission."

    def remove_app_permission(self, app_name: str, permission: str) -> Tuple[bool, str]:
        """Removes a specific permission from an app."""
        app_status = self.device.app_statuses.get(app_name)
        permission = permission.lower()
        if app_status:
            if not hasattr(app_status.permissions, permission):
                return (
                    False,
                    f"Permission '{permission}' not tracked for app '{app_name}'.",
                )
            setattr(app_status.permissions, permission, False)
            return True, f"Permission '{permission}' removed from app '{app_name}'."
        else:
            return False, f"App '{app_name}' not found. Cannot remove permission."

    # --- MMS ---
    @is_tool(ToolType.READ)
    def can_send_mms(self) -> str:
        """Checks if the default messaging app can send MMS messages."""
        result = self._can_send_mms()
        if result:
            return "Your messaging app can send MMS messages."
        else:
            return "Your messaging app cannot send MMS messages."

    def _can_send_mms(self) -> bool:
        """Checks if the default messaging app can send MMS messages."""

        # MMS often needs mobile data path, even if on Wi-Fi
        if not self._get_mobile_data_working():
            return False

        # MMS only works on 3G or higher
        if self.device.network_technology_connected == NetworkTechnology.TWO_G:
            return False

        # The device support Wifi Calling with MMS option, but the carrier does not support it
        if self.device.wifi_calling_enabled and self.device.wifi_calling_mms_over_wifi:
            return False

        # MMSC url not configured
        if self.device.active_apn_settings.mmsc_url is None:
            return False

        # Check messaging app existence and permissions
        msg_app = self.device.app_statuses.get("messaging")
        if msg_app is None:
            return False
        permission_ok = msg_app.permissions.storage and msg_app.permissions.sms
        return permission_ok

    # --- Device Level Actions ---
    @is_tool(ToolType.WRITE)
    def reboot_device(self) -> str:
        """Restarts your phone completely. This can help resolve many temporary software glitches by refreshing all running services and connections."""
        status_update = self._reboot_device()
        return f"{status_update}\nStatus Bar: {self._check_status_bar()}"

    def _reboot_device(self) -> str:
        """
        Simulates rebooting the device by:
        0. Resetting APN settings if required
        1. Resetting network connection status to SEARCHING and triggering a network search
        """
        lines = []

        # 0. Reset APN settings if required
        if self.device.active_apn_settings.reset_at_reboot:
            lines.append("Resetting APN settings...")
            self.device.active_apn_settings = APNSettings()

        # 1. Network Service Restart
        lines.append("Restarting network services...")
        self.device.network_connection_status = NetworkStatus.SEARCHING
        self.simulate_network_search()  # Re-evaluate network connection
        return "\n".join(lines)

    # --- Core Simulation Logic ---
    def simulate_network_search(self):
        """
        Simulates the outcome of a cellular network search based on SIM status.
        This function can be used to update the network_connection_status, technology, and signal strength.
        """
        sim_status = self._check_sim_status()

        if sim_status == SimStatus.ACTIVE:
            self.device.network_connection_status = NetworkStatus.CONNECTED
            pref = self.device.network_mode_preference
            if pref == NetworkModePreference.FOUR_G_5G_PREFERRED:
                five_g_signal = self.surroundings.signal_strength.get(
                    NetworkTechnology.FIVE_G, SignalStrength.NONE
                )
                if five_g_signal == SignalStrength.NONE:
                    self.device.network_technology_connected = NetworkTechnology.FOUR_G
                    self.device.network_signal_strength = (
                        self.surroundings.signal_strength.get(
                            NetworkTechnology.FOUR_G, SignalStrength.NONE
                        )
                    )
                else:
                    self.device.network_technology_connected = NetworkTechnology.FIVE_G
                    self.device.network_signal_strength = five_g_signal
            elif pref == NetworkModePreference.FOUR_G_ONLY:
                self.device.network_technology_connected = NetworkTechnology.FOUR_G
                self.device.network_signal_strength = (
                    self.surroundings.signal_strength.get(
                        NetworkTechnology.FOUR_G, SignalStrength.NONE
                    )
                )
            elif pref == NetworkModePreference.THREE_G_ONLY:
                self.device.network_technology_connected = NetworkTechnology.THREE_G
                self.device.network_signal_strength = (
                    self.surroundings.signal_strength.get(
                        NetworkTechnology.THREE_G, SignalStrength.NONE
                    )
                )
            elif pref == NetworkModePreference.TWO_G_ONLY:
                self.device.network_technology_connected = NetworkTechnology.TWO_G
                self.device.network_signal_strength = (
                    self.surroundings.signal_strength.get(
                        NetworkTechnology.TWO_G, SignalStrength.NONE
                    )
                )
            else:  # Default fallback
                self.device.network_technology_connected = NetworkTechnology.FOUR_G
                self.device.network_signal_strength = (
                    self.surroundings.signal_strength.get(
                        NetworkTechnology.FOUR_G, SignalStrength.NONE
                    )
                )

        elif sim_status in [SimStatus.MISSING]:
            self.device.network_connection_status = NetworkStatus.NO_SERVICE
            self.device.network_technology_connected = NetworkTechnology.NONE
            self.device.network_signal_strength = SignalStrength.NONE

        elif sim_status in [SimStatus.LOCKED_PIN, SimStatus.LOCKED_PUK]:
            self.device.network_connection_status = NetworkStatus.NO_SERVICE
            self.device.network_technology_connected = NetworkTechnology.NONE
            self.device.network_signal_strength = SignalStrength.NONE

        else:  # Should not happen with Enum, but good practice
            self.device.network_connection_status = NetworkStatus.NO_SERVICE
            self.device.network_technology_connected = NetworkTechnology.NONE
            self.device.network_signal_strength = SignalStrength.NONE

        # No network connection if airplane mode is on
        if self.device.airplane_mode:
            self.device.network_connection_status = NetworkStatus.NO_SERVICE
            self.device.network_technology_connected = NetworkTechnology.NONE
            self.device.network_signal_strength = SignalStrength.NONE

        # No network connection if APN is broken
        if self.device.active_apn_settings.apn_name == APNNames.BROKEN:
            self.device.network_connection_status = NetworkStatus.NO_SERVICE
            self.device.network_technology_connected = NetworkTechnology.NONE
            self.device.network_signal_strength = SignalStrength.NONE

        # No network connection if line is not active
        if not self.surroundings.line_active:
            self.device.network_connection_status = NetworkStatus.NO_SERVICE
            self.device.network_technology_connected = NetworkTechnology.NONE
            self.device.network_signal_strength = SignalStrength.NONE

    # --- Payment Request ---
    @is_tool(ToolType.READ)
    def check_payment_request(self) -> str:
        """
        Checks if the agent has sent you a payment request.
        """
        payment_request = self._check_payment_request()
        if payment_request is None:
            return "No payment request has been made."
        return f"You have a payment request for bill {payment_request.bill_id} of {payment_request.amount_due} USD."

    def _check_payment_request(self) -> Optional[PaymentRequest]:
        """
        Checks if a payment request has been made.
        """
        if self.surroundings.payment_request is None:
            return None
        return self.surroundings.payment_request

    @is_tool(ToolType.WRITE)
    def make_payment(self) -> str:
        """
        Makes a payment for the bill that the agent has sent you.
        """
        msg = self._make_payment()
        if msg is None:
            return "You do not have a payment request."
        return msg

    def _make_payment(self) -> Optional[str]:
        """
        Makes a payment for a specific bill.
        """
        payment_request = self._check_payment_request()
        if payment_request is None:
            return None
        payment_request.paid = True
        return f"Payment of {payment_request.amount_due} USD has been made for bill {payment_request.bill_id}."

    # --- Assertion Methods ---
    def assert_airplane_mode_status(self, expected_status: bool) -> bool:
        """
        Assert that the airplane mode status is as expected.
        """
        return self.device.airplane_mode == expected_status

    def assert_service_status(self, expected_status: str) -> bool:
        """
        Assert that the network connection status is as expected.
        """
        return self.device.network_connection_status == NetworkStatus(expected_status)

    def assert_mobile_data_status(self, expected_status: bool) -> bool:
        """
        Assert that the mobile data status is as expected.
        """
        return self._get_mobile_data_working() == expected_status

    def assert_mobile_roaming_status(self, expected_status: bool) -> bool:
        """
        Assert that the roaming status is as expected.
        """
        return self.device.roaming_enabled == expected_status

    def assert_mobile_data_saver_mode_status(self, expected_status: bool) -> bool:
        """
        Assert that the data saver mode status is as expected.
        """
        return self.device.data_saver_mode == expected_status

    def assert_internet_speed(
        self, expected_speed: float, expected_desc: Optional[str] = None
    ) -> bool:
        """
        Assert that the internet speed is as expected.
        """
        speed, desc = self._run_speed_test()
        speed = speed or 0.0
        if expected_desc is None:
            return speed >= expected_speed
        else:
            return speed >= expected_speed and desc.lower() == expected_desc.lower()

    def assert_internet_not_excellent(self) -> bool:
        """
        Assert that the internet speed is not excellent.
        """
        speed, desc = self._run_speed_test()
        return desc.lower() != "excellent"

    def assert_can_send_mms(self, expected_status: bool) -> bool:
        """
        Assert that the default messaging app can send MMS messages.
        """
        return self._can_send_mms() == expected_status

    def assert_mobile_data_usage_exceeded(self, expected_status: bool) -> bool:
        """
        Assert that the mobile data usage exceeded status is as expected.
        """
        return self.surroundings.mobile_data_usage_exceeded == expected_status
