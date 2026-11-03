def analyze_dc(voltage_v, resistance_ohm):
    if resistance_ohm == 0:
        raise ValueError("ความต้านทาน (Resistance) ต้องไม่เท่ากับ 0")
    
    current_a = voltage_v / resistance_ohm
    power_w = voltage_v * current_a
    return {"current_a": current_a, "power_w": power_w}


if __name__ == "__main__":
    result = analyze_dc(12, 6)
    print(f"กระแสไฟฟ้า (Current): {result['current_a']} A")
    print(f"กำลังไฟฟ้า (Power): {result['power_w']} W")


