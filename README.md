# GDG Games - Google Club Event Templates 🎮

Three interactive Google-themed party games built with **React + Vite + Tailwind CSS** (frontend) and **Python Flask** (backend). Designed for GDG events, targeting college students aged 17–21.

---

## 📂 Structure

```
template/
├── game1_truth_or_myth/   → Tech Truth or Myth 🧠
├── game2_old_vs_new/      → Old vs New Tech ⏱️
└── game3_emoji_guess/     → Guess The App by Emoji 🎯
```

Each game has:
```
game_name/
├── frontend/   (React + Vite + Tailwind CSS)
└── backend/    (Python Flask)
```

---

## 🎮 Games

### 1. Tech Truth or Myth 🧠
Participants vote **TRUTH** or **MYTH** on tech statements, then the presenter reveals the answer with a fun explanation.

- 55 questions in pool → **10 random per session** (anti-cheat!)
- Flip-card reveal animation + confetti on correct answer
- Google brand color theme

### 2. Old vs New Tech ⏱️
Two tech products appear — audience has **5 seconds** to guess which one is older!

- 55 product pairs in pool → **10 random per session**
- SVG countdown ring timer
- Year reveal with fun fact after each round

### 3. Guess The App by Emoji 🎯
Giant emojis appear — pick the correct app from 3 options!

- 55 emoji puzzles → **10 random per session** + options shuffled
- Google ecosystem + popular apps
- Confetti burst on correct answer

---

## 🚀 Running a Game

### Frontend
```bash
cd template/game1_truth_or_myth/frontend  # or game2 / game3
npm install
npm run dev
```

### Backend (optional — data is embedded in frontend too)
```bash
cd template/game1_truth_or_myth/backend
pip install -r requirements.txt
python app.py
```

| Game | Frontend Port | Backend Port |
|------|--------------|--------------|
| Truth or Myth | :5173 | :5001 |
| Old vs New | :5174 | :5002 |
| Emoji Guess | :5175 | :5003 |

---

## 🎨 Tech Stack

- **Frontend**: React 18 + Vite + Tailwind CSS + canvas-confetti
- **Backend**: Python Flask + Flask-CORS
- **Design**: Google brand colors, Poppins font, mobile-first (390px)

Made by Mahir Mulani
