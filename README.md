# Uma Devi's Pride Finance Management System

Professional backend API for managing vehicles, loans, and financial records.

## 🚀 **Deployment**

### **Vercel Deployment**
- **Entry Point**: `main.py`
- **Framework**: FastAPI
- **Database**: Supabase

### **Environment Variables**
```bash
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
```

## 📁 **Project Structure**

```
Umadevi-Pride-Finance-Backend/
├── app/                     # Core application modules
│   ├── api/v1/             # API routes
│   │   ├── vehicles.py     # Vehicle management
│   │   ├── auth.py         # Authentication
│   │   ├── dashboard.py    # Dashboard data
│   │   ├── loans.py        # Loan management
│   │   ├── outside_interest.py # Outside interest
│   │   ├── payments.py     # Payment processing
│   │   └── analytics.py    # Analytics & reports
│   ├── core/               # Core functionality
│   ├── database/           # Database operations
│   └── models/             # Data models
├── main.py                  # FastAPI app entry point
├── vercel.json             # Vercel configuration
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🔧 **API Endpoints**

### **Vehicles Management**
- `GET /api/v1/vehicles/getAll` - Get all vehicles
- `POST /api/v1/vehicles/create` - Create new vehicle
- `PUT /api/v1/vehicles/updateDetails/{id}` - Update vehicle
- `DELETE /api/v1/vehicles/delete/{id}` - Delete vehicle
- `POST /api/v1/vehicles/close/{id}` - Close vehicle

### **Authentication**
- `POST /api/v1/auth/login` - User login

### **Dashboard**
- `GET /api/v1/dashboard/overview` - Dashboard overview

### **Loans**
- `GET /api/v1/loans/getAll` - Get all loans

### **Payments**
- `GET /api/v1/payments/getAll` - Get all payments
- `POST /api/v1/payments/create` - Create payment

### **Analytics**
- `GET /api/v1/analytics/summary` - Analytics summary

## 🛠️ **Development**

### **Local Development**
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

### **Vercel Deployment**
1. Push to GitHub
2. Connect Vercel to repository
3. Set environment variables
4. Deploy

## 📚 **Features**

- **Professional API Design** - Clean, RESTful endpoints
- **Modular Architecture** - Well-organized route structure
- **Data Validation** - Pydantic models with constraints
- **Error Handling** - Proper HTTP status codes
- **CORS Support** - Cross-origin request handling
- **Supabase Integration** - Database operations
- **Vercel Ready** - Optimized for serverless deployment