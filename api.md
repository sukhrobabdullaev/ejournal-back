# Ejournal Tizimi va API Hujjati

## 1. Tizimning Umumiy Logikasi (Biznes Jarayon)

**Ejournal** - bu ilmiy maqolalarni (manuscripts) qabul qilish, taqrizchilarga (reviewers) jo'natish, tahririyat qarorini qabul qilish va nashr etish jarayonlarini avtomatlashtiruvchi platforma. Tizim aniq belgilangan **Status Mashinasi (State Machine)** orqali boshqariladi.

**Maqolaning (Submission) hayot tsikli:**
1. **Submitted (Boshlang'ich):** Muallif maqola yuklashni boshlaydi, metadata va fayllarni biriktiradi.
2. **Submitted (Topshirilgan):** Barcha ma'lumotlar to'ldirilib, tahririyatga yuboriladi.
3. **Screening (Ko'rik):** Muharrir (Editor) maqolaning jurnal talablariga mosligini tekshiradi. Mos kelmasa `desk_rejected` qilinadi.
4. **Under Review (Taqrizda):** Maqola taqrizchilarga yuboriladi. Taqrizchilar baholaydi.
5. **Decision Pending (Qaror kutilmoqda):** Taqrizlar yig'ilgach, muharrir yakuniy qaror chiqarish bosqichiga o'tkazadi.
6. **Qaror qabul qilish:**
   - **Accepted:** Maqola qabul qilinadi va `published` (nashr) qilinadi.
   - **Rejected:** Maqola butunlay rad etiladi.
   - **Revision Required:** Muallifga kamchiliklarni to'g'rilash uchun qaytariladi (keyin `resubmitted` qilinadi).

---

## 2. Ruxsatlar va Rollar (Role-Based Access)

| Tizim Roli | Tizimdagi Statusi | Kirish Ruxsati (Qaysi API'lardan foydalana oladi) |
| :--- | :--- | :--- |
| **Public** | Anonim / Tizimga kirmagan | Login, Signup, Email verify, Editorial Board ko'rish |
| **Author** | Email Verified (`True`) | `/api/submissions/` (O'z maqolalarini yaratish, tahrirlash va yuborish) |
| **Reviewer** | `is_approved_reviewer=True` | `/api/reviewer/` (Taqrizlarni qabul qilish/rad etish, baho yozish) |
| **Editor** | `is_approved_editor=True` | `/api/editor/` (Barcha maqolalarni ko'rish, taqrizchi tayinlash, qaror qabul qilish) |
| **Admin** | `is_staff=True` | `/api/admin/` (Tahririyat a'zolarini tasdiqlash yoki rad etish) |

---

## 3. API Endpointlar Ro'yxati

*Base URL:* `http://localhost:8000`

### 3.1. Auth va Profil (Accounts)
| Metod | Endpoint | Ruxsat | Body (So'rov) | Response (Javob) |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/signup` | Public | `{ email, password, full_name, role }` | `201 Created` - Token yuborildi xabari |
| `POST` | `/api/auth/login` | Verified | `{ email, password }` | `200 OK` - `{ access, refresh, user: {...} }` |
| `GET` | `/api/auth/verify-email?token=...` | Public | *Yo'q* | `200 OK` - Email tasdiqlandi |
| `GET` | `/api/me` | Auth | *Yo'q* | `200 OK` - Joriy foydalanuvchi ma'lumotlari |
| `PATCH` | `/api/me` | Auth | `{ full_name, affiliation, country... }` | `200 OK` - Yangilangan profil |

### 3.2. Umumiy (Integrations)
| Metod | Endpoint | Ruxsat | Body (So'rov) | Response (Javob) |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/upload-file` | Auth | `FormData: { file }` | `201 Created` - `{ file_url }` |

### 3.3. Author API (Maqola yuborish)
| Metod | Endpoint | Ruxsat | Body (So'rov) | Response (Javob) |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/topic-areas/` | Auth | *Yo'q* | `200 OK` - Yo'nalishlar ro'yxati |
| `POST` | `/api/submissions/` | Author | `{ title, abstract, topic_area... }` | `201 Created` - Yangi maqola (submitted) |
| `GET` | `/api/submissions/` | Author | *Yo'q* | `200 OK` - Muallifning maqolalari |
| `PATCH` | `/api/submissions/{id}/`| Author | `{ title, abstract... }` | `200 OK` - Qisman yangilangan maqola |
| `POST` | `/api/submissions/{id}/upload-file/`| Author| `FormData: { file, file_type }` | `200 OK` - Biriktirilgan fayl |
| `POST` | `/api/submissions/{id}/submit/` | Author | *Yo'q* | `200 OK` - Status `submitted` ga o'tdi |
| `POST` | `/api/submissions/{id}/resubmit/` | Author | *Yo'q* | `200 OK` - Qayta ishlangan variant yuborildi |

### 3.4. Editor API (Tahririyat)
| Metod | Endpoint | Ruxsat | Body (So'rov) | Response (Javob) |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/editor/submissions/` | Editor | *Yo'q* | `200 OK` - Maqolalar ro'yxati |
| `GET` | `/api/editor/submissions/{id}/`| Editor| *Yo'q* | `200 OK` - Maqola va uning taqrizlari to'liq |
| `POST` | `/api/editor/submissions/{id}/start-screening/` | Editor | *Yo'q* | `200 OK` - Status `screening` |
| `POST` | `/api/editor/submissions/{id}/desk-reject/` | Editor | `{ reason }` | `200 OK` - Maqola rad etildi |
| `POST` | `/api/editor/submissions/{id}/send-to-review/` | Editor | *Yo'q* | `200 OK` - Status `under_review` |
| `POST` | `/api/editor/submissions/{id}/invite-reviewer/`| Editor | `{ reviewer_user_id, due_date }` | `201 Created` - Taqrizchi taklif qilindi |
| `POST` | `/api/editor/submissions/{id}/move-to-decision/`| Editor | *Yo'q* | `200 OK` - Status `decision_pending` |
| `POST` | `/api/editor/submissions/{id}/decision/` | Editor | `{ decision, decision_letter }` | `200 OK` - Yakuniy qaror qabul qilindi |
| `POST` | `/api/editor/submissions/{id}/publish/` | Editor | *Yo'q* | `200 OK` - Maqola nashr etildi |

### 3.5. Reviewer API (Taqrizchi)
| Metod | Endpoint | Ruxsat | Body (So'rov) | Response (Javob) |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/reviewer/assignments/` | Reviewer | *Yo'q* | `200 OK` - Taqriz uchun topshiriqlar |
| `POST` | `/api/reviewer/assignments/{id}/accept/`| Reviewer| *Yo'q* | `200 OK` - Topshiriq qabul qilindi |
| `POST` | `/api/reviewer/assignments/{id}/decline/`| Reviewer| *Yo'q* | `200 OK` - Topshiriq rad etildi |
| `POST` | `/api/reviewer/assignments/{id}/submit-review/`| Reviewer| `{ score, comments, recommendation }` | `200 OK` - Taqriz tizimga kiritildi |

### 3.6. Admin API (Xodim)
| Metod | Endpoint | Ruxsat | Body (So'rov) | Response (Javob) |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/admin/users/{id}/approve-reviewer` | Admin | *Yo'q* | `200 OK` - Reviewer tasdiqlandi |
| `POST` | `/api/admin/users/{id}/approve-editor` | Admin | *Yo'q* | `200 OK` - Editor tasdiqlandi |

---

## 4. Frontend Service Layer Ko'rsatmasi (Qanday chaqiriladi?)

Frontend qismida API'larni to'g'ridan-to'g'ri komponentlar ichidan chaqirmaslik tavsiya etiladi. Buning o'rniga "Service Layer" (Xizmatlar qatlami) yaratilishi kerak. Bu kodni toza va qayta ishlatiladigan qiladi.

**1-qadam: Axios instansiyasini sozlash (`src/services/api/index.ts`)**
Barcha so'rovlarga avtomatik ravishda Authorization (Bearer token) qo'shib yuboradigan yagona axios mijozi yaratiladi.

**2-qadam: Har bir Rol/Kategoriya uchun alohida Service fayllari yaratish**
Modulli yondashuv asosida API'lar bo'linadi:
- `auth.service.ts`: Login, signup, me.
- `author.service.ts`: Muallifning barcha API'lari (`/api/submissions/...`).
- `editor.service.ts`: Muharrir API'lari.
- `reviewer.service.ts`: Taqrizchi API'lari.
- `admin.service.ts`: Admin API'lari.

**Service fayliga namuna (`author.service.ts`):**
```typescript
import api from './index'; // Axios instance

export const authorService = {
  getSubmissions: () => api.get('/api/submissions/'),
  
  createSubmission: (data: any) => api.post('/api/submissions/', data),
  
  updateSubmission: (id: string | number, data: any) => api.patch(`/api/submissions/${id}/`, data),
  
  uploadFile: (id: string | number, formData: FormData) => 
    api.post(`/api/submissions/${id}/upload-file/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
    
  submitArticle: (id: string | number) => api.post(`/api/submissions/${id}/submit/`),
};
```

**3-qadam: Komponent ichida chaqirish (React misolida)**
```tsx
import { useEffect, useState } from 'react';
import { authorService } from '../services/api/author.service';

export const SubmissionsList = () => {
  const [submissions, setSubmissions] = useState([]);

  useEffect(() => {
    authorService.getSubmissions()
      .then(res => setSubmissions(res.data))
      .catch(err => console.error("Xatolik yuz berdi", err));
  }, []);

  return (
    // ... UI qismi
  );
}
```
