# Hyderabad Travel Planner 🌃

A full-stack web application that helps users create personalized Hyderabad travel itineraries based on their destination, budget, interests, mood, travel duration, and preferences.

The application combines curated places stored in PostgreSQL with live place recommendations from the Geoapify Places API and generates a personalized itinerary with Google Maps links.

---

## 🚀 Features

### 🔐 User Authentication
- User registration and login
- Password hashing
- JWT-based authentication for protected APIs
- Flask session management
- Logout functionality
- User-specific data

### 🧭 Personalized Trip Planning
Users can provide:

- Destination
- Budget
- Interests
- Mood
- Travel duration
- Company / travel type

The system then generates a personalized itinerary based on these preferences.

### 📍 Place Recommendations
The application combines:

- Curated Hyderabad places stored in PostgreSQL
- Live places retrieved using the Geoapify Places API

The recommendation system considers factors such as:

- Destination relevance
- User interests
- Mood
- Budget
- Ratings
- Place category
- Live-place availability

### 🗺️ Google Maps Integration
Generated places include Google Maps links so users can easily navigate to recommended locations.

### 🔎 Recent Searches
Users can view their previous trip searches, including:

- Destination
- Budget
- Mood
- Interests
- Travel duration
- Search date

Recent searches are associated with the logged-in user.

### 💾 PostgreSQL Database
The application uses PostgreSQL to store:

- User accounts
- User information
- Recent searches
- Travel-related data

---

## 🛠️ Tech Stack

### Backend
- Python
- Flask
- REST APIs
- JWT Authentication
- PostgreSQL

### Frontend
- HTML
- CSS
- JavaScript
- Tailwind CSS

### APIs
- Geoapify Places API
- Google Maps links

### Tools
- Git
- GitHub
- VS Code

---

## 🏗️ Application Flow

```text
                    ┌───────────────┐
                    │     User      │
                    └───────┬───────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ Register / Login │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │  Authentication  │
                  │ JWT + Session    │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │      Home        │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │  Trip Planner    │
                  │                  │
                  │ Destination      │
                  │ Budget           │
                  │ Interests        │
                  │ Mood             │
                  │ Duration         │
                  └────────┬─────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │ Recommendation Engine   │
              └───────────┬─────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
       ┌──────────────┐       ┌────────────────┐
       │ PostgreSQL   │       │ Geoapify API   │
       │ Curated Data │       │ Live Places    │
       └──────┬───────┘       └───────┬────────┘
              │                       │
              └───────────┬───────────┘
                          ▼
                 ┌─────────────────┐
                 │   Itinerary     │
                 │   Generation    │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ Result + Maps   │
                 │ Links           │
                 └─────────────────┘
