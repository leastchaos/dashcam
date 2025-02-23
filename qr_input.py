import time
import pyautogui

# Simulate reading QR code data (replace with actual QR code reading)
qr_code_data = r"""{"template_name": "Gemetric", "lot_name": "PMTF 6_Functionality_XY1-G +20.00D", "nominals":{"Sphere": "20.72495|0.19995", "Cylinder": "0|0.2618","MTF_F_A1_FA_S": 0.28,"MTF_I_A1_FA_S": 0.09,"MTF_N_A1_FA_S": 0.13,"MTF_F_A2_FA_S": 0.4,"MTF_F_A1_FA_F": 0.28,"MTF_I_A1_FA_F": 0.09,"MTF_N_A1_FA_F": 0.13,"MTF_F_A2_FA_F": 0.4}}"""

time.sleep(2)
pyautogui.typewrite(qr_code_data)

# Press Enter
pyautogui.press('enter')