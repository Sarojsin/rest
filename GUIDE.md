# Restaurant Management System - Complete Guide

## Quick Start
### Backend
`ash
cd backend
pip install -e .[dev]
pip install argon2-cffi PyJWT httpx
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
` 
- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

### Frontend
`ash
cd apps/web
npm install
npm run dev -- --host 127.0.0.1 --port 5173
` 
- Website: http://127.0.0.1:5173

## Demo Credentials
| Role | Email | Password |
|---|---|---|
| Owner | owner@harbor.example | HarborOwner!1 |
| Manager | manager@harbor.example | HarborManager!1 |
| Waiter | waiter@harbor.example | HarborWaiter!1 |
| Kitchen | kitchen@harbor.example | HarborKitchen!1 |
| Cashier | cashier@harbor.example | HarborCashier!1 |

## Customer QR Flow
1. Scan QR or open /t/{qrToken}
2. Browse menu and place order (needs staff confirmation)
3. Track status at /status/{statusToken}
4. View bill, cancel order, rate food

## QR Tokens
- table-harbor-1-alpha (T1)
- table-harbor-2-bravo (T2)
- table-harbor-3-charlie (T3)
- table-harbor-4-delta (T4)
- table-harbor-5-echo (T5)
- table-harbor-6-foxtrot (T6)

## Staff Workflow
- Waiter: Pending orders -> Accept/Reject, manage tables
- Kitchen: New -> Preparing -> Ready -> Served
- Cashier: Issue bills, record cash payments
- Manager/Owner: Menu management, reports
