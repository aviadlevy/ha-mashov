# הוספת לוגו משוב ל-Home Assistant Brands

## קבצים מוכנים להוספה

הקבצים הבאים מוכנים להוספה ל-Home Assistant brands repository:

### מיקום: `custom_integrations/mashov/`

- `icon.png` - אייקון 256x256 פיקסלים
- `icon@2x.png` - אייקון 512x512 פיקסלים (גרסה גדולה)
- `logo.png` - לוגו בגודל סטנדרטי
- `logo@2x.png` - לוגו בגודל גדול

## הוראות הוספה ל-Home Assistant Brands

1. **Fork את ה-repository**:
   - לך ל: https://github.com/home-assistant/brands
   - לחץ על "Fork" ליצירת עותק

2. **Clone את ה-fork שלך**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/brands.git
   cd brands
   ```

3. **הוסף את הקבצים**:
   ```bash
   mkdir -p custom_integrations/mashov
   cp /path/to/our/files/* custom_integrations/mashov/
   ```

4. **Commit ו-Push**:
   ```bash
   git add custom_integrations/mashov/
   git commit -m "Add logo for mashov integration"
   git push origin master
   ```

5. **צור Pull Request**:
   - לך ל-fork שלך ב-GitHub
   - לחץ על "New Pull Request"
   - השווה את ה-fork שלך ל-upstream master
   - שלח את ה-PR לבדיקה

## מידע על האינטגרציה

- **Domain**: mashov
- **Name**: משוב (Mashov)
- **Type**: Custom Integration
- **Repository**: https://github.com/NirBY/ha-mashov
- **Description**: אינטגרציה למשוב - מערכת ניהול בתי ספר ישראלית
