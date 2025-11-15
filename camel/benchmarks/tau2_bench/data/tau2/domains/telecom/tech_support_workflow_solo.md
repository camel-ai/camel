# Phone Device - Technical Support Troubleshooting Workflow

## Introduction

This document provides a structured workflow for diagnosing and resolving phone technical issues. As an agent, you have direct access to the user's device and can perform these actions yourself. Follow these paths based on the user's problem description. Each step includes specific actions you should take to check or modify settings.

Make sure you try all the relevant resolution steps before transferring the user to a human agent.

## Available Actions Reference
Since you have access to the user's device, you can perform the following actions directly:

### Diagnostic Actions (Read-only)
1. **Check Status Bar** - Shows what icons are currently visible in the phone's status bar (the area at the top of the screen). Displays network signal strength, mobile data status (enabled, disabled, data saver), Wi-Fi status, and battery level.
2. **Check Network Status** - Checks the phone's connection status to cellular networks and Wi-Fi. Shows airplane mode status, signal strength, network type, whether mobile data is enabled, and whether data roaming is enabled. Signal strength can be "none", "poor" (1bar), "fair" (2 bars), "good" (3 bars), "excellent" (4+ bars).
3. **Check Network Mode Preference** - Checks the phone's network mode preference. Shows the type of cellular network the phone prefers to connect to (e.g., 5G, 4G, 3G, 2G).
4. **Check SIM Status** - Checks if the SIM card is working correctly and displays its current status. Shows if the SIM is active, missing, or locked with a PIN or PUK code.
5. **Check Data Restrictions** - Checks if the phone has any data-limiting features active. Shows if Data Saver mode is on and whether background data usage is restricted globally.
6. **Check APN Settings** - Checks the technical APN settings the phone uses to connect to the carrier's mobile data network. Shows current APN name and MMSC URL for picture messaging.
7. **Check Wi-Fi Status** - Checks Wi-Fi connection status. Shows if Wi-Fi is turned on, which network it's connected to (if any), and the signal strength.
8. **Check Wi-Fi Calling Status** - Checks if Wi-Fi Calling is enabled on the device. This feature allows making and receiving calls over a Wi-Fi network instead of using the cellular network.
9. **Check VPN Status** - Checks if a VPN (Virtual Private Network) connection is active. Shows if a VPN is active, connected, and displays any available connection details.
10. **Check Installed Apps** - Returns the name of all installed apps on the phone.
11. **Check App Status** - Checks detailed information about a specific app. Shows its permissions and background data usage settings.
12. **Check App Permissions** - Checks what permissions a specific app currently has. Shows if the app has access to features like storage, camera, location, etc.
13. **Run Speed Test** - Measures the current internet connection speed (download speed). Provides information about connection quality and what activities it can support. Download speed can be "unknown", "very poor", "poor", "fair", "good", or "excellent".
14. **Can Send MMS** - Checks if the messaging app can send MMS messages.

### Fix Actions (Write/Modify)
1. **Set Network Mode** - Changes the type of cellular network the phone prefers to connect to (e.g., 5G, 4G, 3G). Higher-speed networks (5G, 4G) provide faster data but may use more battery.
2. **Toggle Airplane Mode** - Turns Airplane Mode ON or OFF. When ON, it disconnects all wireless communications including cellular, Wi-Fi, and Bluetooth.
3. **Reseat SIM Card** - Simulates removing and reinserting the SIM card. This can help resolve recognition issues.
4. **Toggle Mobile Data** - Turns the phone's mobile data connection ON or OFF. Controls whether the phone can use cellular data for internet access when Wi-Fi is unavailable.
5. **Toggle Data Roaming** - Turns Data Roaming ON or OFF. When ON, roaming is enabled and the phone can use data networks in areas outside the carrier's coverage.
6. **Toggle Data Saver** - Turns Data Saver mode ON or OFF. When ON, it reduces data usage, which may affect data speed.
7. **Set APN Settings** - Sets the APN settings for the phone.
8. **Reset APN Settings** - Resets APN settings to the default settings.
9. **Toggle Wi-Fi** - Turns the phone's Wi-Fi radio ON or OFF. Controls whether the phone can discover and connect to wireless networks for internet access.
10. **Toggle Wi-Fi Calling** - Turns Wi-Fi Calling ON or OFF. This feature allows making and receiving calls over Wi-Fi instead of the cellular network, which can help in areas with weak cellular signal.
11. **Connect VPN** - Connects to the VPN (Virtual Private Network).
12. **Disconnect VPN** - Disconnects any active VPN (Virtual Private Network) connection. Stops routing internet traffic through a VPN server, which might affect connection speed or access to content.
13. **Grant App Permission** - Gives a specific permission to an app (like access to storage, camera, or location). Required for some app functions to work properly.
14. **Reboot Device** - Restarts the phone completely. This can help resolve many temporary software glitches by refreshing all running services and connections.

## Initial Problem Classification

Determine which category best describes the user's issue:

1. **No Service/Connection Issues**: Phone shows "No Service" or cannot connect to the network
2. **Mobile Data Issues**: Cannot access internet or experiencing slow data speeds
3. **Picture/Group Messaging (MMS) Problems**: Unable to send or receive picture messages

For multiple issues, address basic connectivity first.

## Path 1: No Service / No Connection Troubleshooting

### Step 1.0: Check if user is facing a no service issue
If service is available, the status bar will not display 'no signal' or 'airplane mode'.
- Check the status bar
- If status bar shows that service is available, the user is not facing a no service issue.
- If status bar shows that service is not available, proceed to Step 1.1

### Step 1.1: Check Airplane Mode and Network Status
Check the phone's connection to the cellular network and Wi-Fi. This will show if Airplane Mode is on, signal strength, and other connection details.

**If Airplane Mode is ON:**
- Turn Airplane Mode OFF
- Check the status bar to see if service is restored

**If Airplane Mode is OFF:**
- Proceed to Step 1.2

### Step 1.2: Verify SIM Card Status
Check if the SIM card is working correctly. Determine if it's missing, locked, or active.

**If SIM shows as MISSING:**
- Re-seat the SIM card by removing and re-inserting it
- Check that the SIM card is ACTIVE.
- Check the status bar to see if service is restored

**If SIM is LOCKED with PIN/PUK:**
- Escalate to technical support for assistance with SIM security

**If SIM is ACTIVE and working:**
- Proceed to Step 1.3

### Step 1.3: Try to reset APN settings
If basic connectivity issues persist:

- Reset APN settings to default
- Restart the device
- Check the status bar to see if service is restored

**If still not resolved:**
- Proceed to Step 1.4

### Step 1.4: Check Line Suspension
No service can be due to a suspended line.

**If the line is suspended:**
- Follow the instructions in the main policy for more information on line suspension and how to lift the suspension.
- If you are able to lift the suspension:
    - Check the status bar to see if service is restored.
- If you are not able to lift the suspension:
    - Escalate to technical support.

**If still not resolved:**
- Escalate to technical support

## Path 2: Unavailable or Slow Mobile Data Troubleshooting

Note: This path does not cover wifi data issues.

### Step 2.0: Check if user is facing a data issue

When mobile data is unavailable a speed test should return 'no connection'.
If data is available, a speed test will also return the data speed. Any speed below 'Excellent' is considered slow.
- Path 2.1 check for unavailable mobile data issues.
- Path 2.2 check for slow data issues.

## Path 2.1: Unavailable Mobile Data Troubleshooting

### Step 2.1.0: Check if user is facing an unavailable mobile data issue

- Run a speed test.
- If speed test returns 'no connection', mobile data is unavailable. 
    - Follow Path 2.1.
    - Once problem is resolved proceed, if speed is not 'Excellent', follow Path 2.2.
- If speed test returns the data speed, mobile data is available.
    - If speed is 'Excellent', the user is not facing a mobile data issue.
    - For any other speed ('Poor', 'Fair', 'Good'), mobile data might be slow and you must follow Path 2.2.

### Step 2.1.1: Verify Service Issue
Check if the phone has cellular service. Mobile data requires at least some cellular network connection.

- Follow Path 1 (No Service / No Connection) troubleshooting steps first.
- When you have confirmed that service is available, check if mobile data issue persists.
    - Rerun the speed test and check data connectivity.
    - If there is still no connectivity, proceed to Step 2.1.2.

### Step 2.1.2: Verify if user is traveling
Check if the user is outside their usual service area. 

**If the User is not traveling:**
- Proceed to Step 2.1.3

**If the User is traveling:**
- Verify if Data Roaming is enabled to allow data usage on other networks.


**If Data Roaming is OFF:**
- Turn Data Roaming ON
- Rerun the speed test and check data connectivity.

**If Data Roaming is ON but not working:**
- Verify that the line associated with the phone number the user provided is roaming enabled.
    - If the line is not roaming enabled, enable it at no cost for the user
- Rerun the speed test and check data connectivity.
    - If there is still no connectivity, proceed to Step 2.1.3.

**If Data Roaming is ON and enabled but connectivity is not working:**
- Proceed to Step 2.1.3

### Step 2.1.3: Check Mobile Data Settings
**If Mobile Data is OFF:**
- Turn Mobile Data ON
- Rerun the speed test and check data connectivity.
    - If there is still no connectivity, proceed to Step 2.1.4.

**If Mobile Data is ON but not working:**
- Proceed to Step 2.1.4

### Step 2.1.4: Check Data Usage
Check if, for the line associated with the phone number the user provided, the user's data usage has exceeded their data limit.

**If Data Usage is EXCEEDED:**
- Check if user gave permission to change another plan or refuel data.
- Follow the instructions in the main policy for more information on data refueling and plan change.
- If you are able to refuel data or change to plan with a higher data limit:
    - Rerun the speed test and check data connectivity.
    - If there is still no connectivity, transfer to technical support.
- If you cannot refuel data or change to plan with a higher data limit (not allowed or user does not want to):
    - Escalate to technical support.

**If Data Usage is NOT EXCEEDED:**
- Rerun the speed test and check data connectivity.
    - If there is still no connectivity, transfer to technical support.

## Path 2.2: Slow Mobile Data Troubleshooting

### Step 2.2.0: Check if user is facing a slow data issue
When mobile data is available but speed is anything other than 'Excellent', the user is facing a slow data issue.
- Run a speed test.
- If speed test returns 'no connection', mobile data is unavailable. 
    - Follow Path 2.1.
- If speed test returns the data speed, mobile data is available.
    - If speed is 'Excellent', the user is not facing a slow data issue.
    - For any other speed ('Poor', 'Fair', 'Good'), mobile data might be slow and you must follow Path 2.2.

### Step 2.2.1: Check Data Restriction Settings
Check if any settings are limiting data usage, like Data Saver mode.

**If Data Saver is ON:**
- Turn Data Saver mode OFF
- Rerun the speed test and check if speed improved to 'Excellent'.
    - If this is not the case, proceed to Step 6.
**If Data Saver is OFF:**
- Proceed to Step 6

### Step 2.2.2: Check Network Mode Preference
Check what type of cellular network the phone prefers. Using older modes like 2G/3G can significantly limit speed.

**If set to older network types (2G/3G only):**
- Change the network preference to an option that includes 5G
- Rerun the speed test and check if speed improved to 'Excellent'.
    - If this is not the case, proceed to Step 7.

**If already on optimal setting:**
- Proceed to Step 7

### Step 2.2.3: Check for Active VPN
Check if a VPN (Virtual Private Network) is active which might affect connection quality.

**If VPN is active:**
- Turn off the current VPN connection
- Rerun the speed test and check if speed improved to 'Excellent'.
    - If this is not the case, escalate to technical support.

**If no VPN or disconnecting didn't help:**
- Escalate to technical support. 

## Path 3: MMS (Picture/Group Messaging) Troubleshooting

### Step 3.0: Check if user is facing a MMS issue
When MMS is not working, the user will not be able to send or receive picture messages.

- Check if an MMS message can be sent using the default messaging app.
    - If this is working, the user is not facing a MMS issue.
    - If this is not working, proceed to Step 3.1.

### Step 3.1: Verify Network Service Status
Check if the phone has cellular service. MMS requires at least some cellular network connection.

- Follow Path 1 (No Service / No Connection) troubleshooting steps first.
- Once you have confirmed that service is available, check if issue persists:
    - Check if an MMS message can be sent using the default messaging app.

**If service is available:**
- Proceed to Step 3.2

### Step 3.2: Verify Mobile Data Status
Mobile data is required for MMS.

- Use Path 2.1 (Unavailable Mobile Data) troubleshooting steps to check if mobile data connectivity is working. Do not worry about speed, focus on connectivity.
- Once you have confirmed that mobile data connectivity is working, check if MMS issue persists:
    - Try to send an MMS message using default messaging app again.

### Step 3.3: Check Network Technology
Check what type of cellular network the phone is connected to. MMS requires at least 3G or higher technology.

**If connected to 2G network only:**
- Change network mode to include at least 3G/4G/5G
- Try to send an MMS message using default messaging app again.

**If on 3G or higher network:**
- Proceed to Step 3.4


### Step 3.4: Check Wi-Fi Calling Status
Check if Wi-Fi Calling is enabled, as it may interfere with MMS functionality.

**If Wi-Fi Calling is ON:**
- Turn Wi-Fi Calling OFF
- Try to send an MMS message using default messaging app again.

**If Wi-Fi Calling is OFF or turning it off didn't help:**
- Proceed to Step 3.5

### Step 3.5: Verify Messaging App Permissions
Check that the default messaging app has the required permissions - specifically both storage and SMS permissions.

**If either storage or SMS permission is missing:**
- Grant both required permissions to the messaging app
- Try to send an MMS message using default messaging app again.

**If all permissions are granted:**
- Proceed to Step 3.6

### Step 3.6: Check APN Settings
Check the technical settings (APNs) the phone uses to connect to the carrier's mobile data network.

**Specifically check for:**
- MMSC URL configuration (must be present for MMS to work)

**If MMSC URL is missing:**
- Reset APN settings to carrier defaults
- Try to send an MMS message using default messaging app again.

**If issues persist after checking all above:**
- Escalate to technical support 