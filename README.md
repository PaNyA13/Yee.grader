# Competitive Programming Grader (FastAPI + PDF + Scoring + Auth)

## ระบบคะแนน
- **คะแนนเต็ม**: 100 คะแนนต่อโจทย์ (ปรับได้)
- **คะแนนย่อย**: แบ่งตามจำนวน testcases
- **Partial Scoring**: ได้คะแนนตามจำนวน testcases ที่ผ่าน
- **ไม่มี Penalty**: ไม่หักคะแนนจากการส่งผิด

## ระบบผู้ใช้
- **Login**: ใช้ username/password
- **เปลี่ยนชื่อ**: ได้ 2 ครั้งต่อบัญชี
- **Admin**: เฉพาะ admin อัปโหลดโจทย์ได้

## ภาษาที่รองรับ
- C (ต้องมี `gcc` ใน PATH)
- C++ (ต้องมี `g++` ใน PATH)

## Setup (Windows)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload


cd E:\grader\grader
venv\Scripts\activate
uvicorn app.main:app --reload
```

- เปิดที่ `http://127.0.0.1:8000`

## ฟีเจอร์
- ระบบล็อกอิน/สมัครสมาชิก
- อัปโหลดโจทย์เป็น PDF พร้อม testcases (เฉพาะ admin)
- ระบบคะแนนแบบยืดหยุ่นและ Leaderboard
- ดู PDF ในเบราว์เซอร์