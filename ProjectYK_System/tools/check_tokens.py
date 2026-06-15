import os
import sys
import json
import glob
from datetime import datetime

# บังคับใช้ UTF-8 สำหรับ stdout เพื่อป้องกันปัญหา Unicode บน Windows Console
try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# กำหนดสีกราฟิกบน Terminal
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_CYAN = "\033[96m"
COLOR_MAGENTA = "\033[95m"
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"

def get_latest_transcript_dir():
    """ค้นหาโฟลเดอร์ของ Conversation ล่าสุดในระบบ"""
    home_dir = os.path.expanduser("~")
    base_path = os.path.join(home_dir, ".gemini", "antigravity-cli", "brain")
    
    if not os.path.exists(base_path):
        # ลองค้นหาแบบ relative หรือ fallback ในกรณีอื่น
        fallback_path = r"C:\Users\guole\.gemini\antigravity-cli\brain"
        if os.path.exists(fallback_path):
            base_path = fallback_path
        else:
            return None
            
    # ค้นหาไฟล์ transcript_full.jsonl ทั้งหมดและหาอันที่มีการแก้ไขล่าสุด
    search_pattern = os.path.join(base_path, "*", ".system_generated", "logs", "transcript_full.jsonl")
    files = glob.glob(search_pattern)
    
    if not files:
        # ลองค้นหา transcript.jsonl เผื่อไม่มี full
        search_pattern = os.path.join(base_path, "*", ".system_generated", "logs", "transcript.jsonl")
        files = glob.glob(search_pattern)
        
    if not files:
        return None
        
    # เรียงลำดับตามเวลาแก้ไขล่าสุด (mtime)
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

def estimate_tokens(text):
    """
    ประมาณการจำนวน Token ของข้อความ
    - ภาษาอังกฤษ/โค้ด (ASCII/UTF-8 ทั่วไป): ~4 ตัวอักษร = 1 Token
    - ภาษาไทย: ~1.5 ตัวอักษร = 1 Token (สำหรับ Tokenizer ปัจจุบันของ Gemini)
    """
    if not text:
        return 0
        
    ascii_chars = 0
    non_ascii_chars = 0
    
    for char in text:
        if ord(char) < 128:
            ascii_chars += 1
        else:
            non_ascii_chars += 1
            
    tokens = (ascii_chars / 4.0) + (non_ascii_chars / 1.5)
    return int(tokens)

def parse_transcript(file_path):
    """อ่านและประเมินสถิติจากไฟล์ Transcript JSONL"""
    total_tokens = 0
    turns_count = 0
    steps_count = 0
    tool_calls_count = 0
    file_reads_count = 0
    
    user_tokens = 0
    model_tokens = 0
    system_tokens = 0
    
    user_turns = 0
    model_turns = 0
    
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                step = json.loads(line.strip())
                steps_count += 1
                
                content = step.get("content", "")
                step_type = step.get("type", "")
                source = step.get("source", "")
                
                # นับการใช้เครื่องมือ
                tool_calls = step.get("tool_calls", [])
                if tool_calls:
                    tool_calls_count += len(tool_calls)
                    for call in tool_calls:
                        if call.get("name") in ["view_file", "read_url_content", "read_browser_page"]:
                            file_reads_count += 1
                
                # ประมาณการ Token ในขั้นนี้
                tokens = estimate_tokens(content)
                total_tokens += tokens
                
                if source == "USER_EXPLICIT" or step_type == "USER_INPUT":
                    user_tokens += tokens
                    user_turns += 1
                    turns_count += 1
                elif source == "MODEL" or step_type == "PLANNER_RESPONSE":
                    model_tokens += tokens
                    model_turns += 1
                    turns_count += 1
                else:
                    system_tokens += tokens
                    
            except Exception:
                continue
                
    return {
        "total_tokens": total_tokens,
        "steps_count": steps_count,
        "turns_count": turns_count,
        "user_turns": user_turns,
        "model_turns": model_turns,
        "tool_calls_count": tool_calls_count,
        "file_reads_count": file_reads_count,
        "breakdown": {
            "user": user_tokens,
            "model": model_tokens,
            "system": system_tokens
        }
    }

def print_status_line(stats, limit=1000000):
    """พิมพ์ Statusline แถบแสดงสถานะและเปอร์เซ็นต์โทเค็นอย่างสวยงาม"""
    used = stats["total_tokens"]
    percent = (used / limit) * 100
    remaining = limit - used
    
    # กำหนดสีตามระดับเปอร์เซ็นต์การใช้งาน
    if percent < 50:
        color = COLOR_GREEN
        status_text = "SAFE (Normal)"
    elif percent < 80:
        color = COLOR_YELLOW
        status_text = "WARNING (Caution)"
    else:
        color = COLOR_RED
        status_text = "CRITICAL (Please open a new chat)"
        
    # วาดแถบ Progress Bar (ความกว้าง 30 ช่องอักษร) - ใช้ตัวอักษร ASCII ที่ปลอดภัยต่อทุก Console
    bar_width = 30
    filled_width = int(round((percent / 100) * bar_width))
    filled_width = min(filled_width, bar_width)  # ป้องกันกรณีเกิน 100%
    bar = "=" * filled_width + "-" * (bar_width - filled_width)
    
    # จัดหน้าจอเอาต์พุตให้สวยงาม
    print("\n" + "=" * 60)
    print(f"{COLOR_BOLD}{COLOR_CYAN}[AI] Project YK - Context Window & Token Monitor{COLOR_RESET}")
    print("=" * 60)
    
    # แถบ Progress Bar หลัก (Status Line)
    print(f"Status: {color}{COLOR_BOLD}{status_text}{COLOR_RESET}")
    print(f"Tokens: {color}[{bar}] {percent:.1f}%{COLOR_RESET} ({used:,} / {limit:,} tokens)")
    print(f"Remaining: {COLOR_BOLD}{COLOR_GREEN if remaining > 0 else COLOR_RED}{remaining:,}{COLOR_RESET} tokens left before limit")
    print("-" * 60)
    
    # ข้อมูลสถิติและประเภท
    print(f"Conversation Turns : {COLOR_BOLD}{stats['turns_count']}{COLOR_RESET} (User: {stats['user_turns']} | Model: {stats['model_turns']})")
    print(f"Tool executions    : {COLOR_BOLD}{stats['tool_calls_count']}{COLOR_RESET} calls (Read operations: {stats['file_reads_count']})")
    print(f"Estimated usage    : User context: {stats['breakdown']['user']:,} | Model outputs: {stats['breakdown']['model']:,} | System: {stats['breakdown']['system']:,}")
    print("-" * 60)
    
    # คำแนะนำแนวทางบริหารจัดการ Context ตามกฎ AGENTS.md
    if percent >= 75:
        print(f"{COLOR_RED}{COLOR_BOLD}[!] WARNING: Context ของคุณกำลังจะเต็มตามกฎของโครงการ!{COLOR_RESET}")
        print("  1. บันทึกงานปัจจุบันลงใน 'NEXT_ACTION_PLAN.md'")
        print("  2. ทำการสรุปงานสั้นๆ (Handoff)")
        print("  3. ปิดแชตปัจจุบันแล้วเปิดแชตใหม่ เพื่อล้างประวัติการสนทนา")
    else:
        print(f"{COLOR_GREEN}[v] Context Status Normal: สนทนาต่อได้ตามปกติ (เน้นคุยทีละหัวข้อสั้นและตรงประเด็น){COLOR_RESET}")
    print("=" * 60 + "\n")

def main():
    # กำหนดขีดจำกัด Context ของ Gemini (มาตรฐาน 1,000,000 สำหรับ Flash และ 2,000,000 สำหรับ Pro)
    limit = 1000000
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass
            
    transcript_file = get_latest_transcript_dir()
    
    if not transcript_file:
        print(f"{COLOR_RED}[x] ไม่พบประวัติสนทนาในระบบ หรือ Directory ของ Antigravity ไม่ตรง{COLOR_RESET}")
        print("กรุณาตรวจสอบว่ามีประวัติการสนทนาอยู่บนเครื่องของคุณ")
        return
        
    # วิเคราะห์ไฟล์
    try:
        stats = parse_transcript(transcript_file)
        print_status_line(stats, limit)
    except Exception as e:
        print(f"{COLOR_RED}[x] เกิดข้อผิดพลาดในการวิเคราะห์ไฟล์: {e}{COLOR_RESET}")

if __name__ == "__main__":
    # เปิดใช้งาน ANSI escape sequences สำหรับระบายสีใน Command Prompt บน Windows
    if sys.platform == "win32":
        os.system("color")
    main()
