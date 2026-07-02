# Oatside engine (vendored)

- `build_oatside_reports.py` = สำเนา **byte-identical** จาก `Oatside/build_oatside_reports.py` (ราก repo)
  — **ห้ามแก้เนื้อไฟล์นี้ตรงๆ** (กติกา 60 แพตช์สะสม): แก้ที่ต้นทางแล้ว copy มาทับ + deploy
- `oatside_config.json` + `oatside_billing_overrides.json` = เงื่อนไขที่หน้า /oatside/settings แก้ (มี backup .bak-* ทุกครั้ง)
- engine เขียน output ที่โฟลเดอร์นี้: `Oatside_PG_Trip_Summary_By_Site.xlsx` + `TransportRateCalculator/reports/oatside-apr2026/` (HTML)
- ระบบเรียกผ่าน `services/oatside_runner.py` (subprocess + env OATSIDE_ORIGIN/OATSIDE_DEST) — ไม่ import เข้า process แอป
