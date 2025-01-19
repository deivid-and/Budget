 Wise Budget Tracker

Wise Budget Tracker is a tool for managing your finances. Track daily, weekly, and monthly budgets, fetch transactions from Wise API, and add manual transactions for complete budget control.
#
---

## Quick Start for End Users

### 📥 Download and Run

1. **Clone** the repository:
   ```bash
   git clone https://github.com/deivid-and/Wise-Budget-Tracker.git
   cd Wise-Budget-Tracker
   ```
2. **Run the Application**:
   ```bash
   python run.py
   ```
3. **Access the App**:
   Open your browser and visit:
   ```
   http://127.0.0.1:5000
   ```

---

## 🚀 Features

- **Custom Budgets**  
  Create daily, weekly, and monthly budgets.
- **Automatic Updates**  
  Fetch transactions from Wise API and update spending automatically.
- **Manual Transactions**  
  Add cash expenses or custom transactions with date and time.
- **Transaction Control**  
  Exclude or include transactions for precise budget calculations.

---

## 🔧 Developer Setup

### 🌀 Clone the Repository

```bash
git clone https://github.com/deivid-and/Wise-Budget-Tracker.git
cd Wise-Budget-Tracker
```

### 🛠️ Set Up Environment

#### On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

#### On Linux/Mac:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 📦 Initialize the Database

```bash
python -c "from app.models import init_db; init_db()"
```

### ▶️ Run the Application

```bash
python run.py
```
Open your browser and visit:
```http://127.0.0.1:5000```

---

## 📋 Usage

1. **Create a Budget**  
   Select a period (Daily, Weekly, Monthly), set the amount, and submit.
2. **Track Spending**  
   View API and manual transactions in your budget.
3. **Add Manual Transactions**  
   Log cash expenses with date and time.
4. **Manage Transactions**  
   Exclude or delete transactions from the budget.

---

## 🛡️ Security

- Ensure your `.env` file is never committed:
  ```plaintext
  .env
  ```
- Rotate API keys if they were ever exposed.

---

## 🤝 Contributing

1. Fork the repository.
2. Create a new branch:
   ```bash
   git checkout -b feature-branch
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add feature"
   ```
4. Push and open a pull request:
   ```bash
   git push origin feature-branch
   ```

---

## 📄 License

This project is open-source under the MIT License.

---

## 🌐 Future Updates

- **Webhook Integration**  
  Real-time transaction updates from Wise API.
- **Spending Notifications**  
  Get notified when approaching budget limits.

