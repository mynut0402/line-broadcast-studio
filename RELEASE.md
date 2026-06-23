# การปล่อยเวอร์ชันใหม่

ระบบอัปเดตอ่านเวอร์ชันล่าสุดจาก GitHub Releases ของ
`mynut0402/line-broadcast-studio`

เมื่อต้องการปล่อยอัปเดต ให้ commit และ push งานล่าสุด จากนั้นสร้าง tag ใหม่:

```powershell
git tag v1.0.1
git push origin v1.0.1
```

GitHub Actions จะ Build ไฟล์ `LINE Broadcast Studio.exe` และสร้าง Release
ให้อัตโนมัติ โปรแกรมที่ติดตั้งอยู่จะตรวจพบเวอร์ชันนี้เมื่อเปิดครั้งถัดไป

หมายเลข tag ใหม่ต้องมากกว่าเวอร์ชันก่อนหน้า เช่น `v1.0.1`, `v1.1.0`, `v2.0.0`
