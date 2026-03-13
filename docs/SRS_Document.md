# SMART COLLEGE CANTEEN MANAGEMENT SYSTEM

## Software Requirement Specification (SRS) Document

---

# CONTENTS

i. Declaration
ii. Acknowledgement  
iii. Abstract
iv. List of Figures

---

## i. Declaration

I hereby declare that the project work entitled **"Smart College Canteen Management System"** submitted to the Department of Computer Science is a record of original work done by me under the guidance of my project guide. This project work is submitted in partial fulfillment of the requirements for the award of the degree.

Date: February 2026

---

## ii. Acknowledgement

I would like to express my sincere gratitude to my project guide for their valuable guidance and support throughout the development of this project. I am also thankful to my institution for providing the necessary resources and infrastructure.

Special thanks to my friends and family for their constant encouragement and support during this project.

---

## iii. Abstract

The **Smart College Canteen Management System** is a web-based application designed to digitize and streamline the food ordering process in a college canteen. The system eliminates traditional queuing problems by allowing students and staff to browse menus, place orders online, make payments, and track order status in real-time.

The application features user authentication with role-based access, a comprehensive menu management system with veg/non-veg filtering, cart functionality, multiple payment options (Cash, Wallet, Online UPI/Card), delivery options to classrooms, and order history tracking. Built using Django framework with MySQL database, the system provides a modern, responsive user interface accessible from any device.

**Keywords:** Canteen Management, Online Food Ordering, Django, MySQL, Web Application

---

## iv. List of Figures

| Figure No. | Description | Page No. |
|------------|-------------|----------|
| Fig 1.1 | System Architecture | - |
| Fig 2.1 | Use Case Diagram | - |
| Fig 3.1 | Context Flow Diagram | - |
| Fig 3.2 | Level 0 DFD | - |
| Fig 3.3 | Level 1 DFD - User Module | - |
| Fig 3.4 | Level 1 DFD - Admin Module | - |
| Fig 3.5 | ER Diagram | - |
| Fig 4.1 | Home Page Screenshot | - |
| Fig 4.2 | Menu Page Screenshot | - |
| Fig 4.3 | Cart Page Screenshot | - |
| Fig 4.4 | Payment Page Screenshot | - |

---

# CHAPTER 1: SYNOPSIS

## 1.1 Title of the Project

**Smart College Canteen Management System**

---

## 1.2 Introduction of the Project

The Smart College Canteen Management System is a comprehensive web-based solution designed to modernize the traditional canteen ordering process in educational institutions. 

In conventional canteen systems, students and staff face numerous challenges:
- Long queues during peak hours
- Limited menu visibility
- Cash handling issues
- No order tracking
- Manual record keeping errors

This project addresses these challenges by providing a digital platform where users can:
- Browse the complete menu with images and descriptions
- Filter items by category (Breakfast, Lunch, Snacks, Beverages, Desserts)
- Filter items by dietary preference (Veg/Non-Veg)
- Add items to cart and checkout seamlessly
- Choose from multiple payment options
- Track order status in real-time
- Get food delivered to classrooms

---

## 1.3 Objective of the Project

The main objectives of this project are:

1. **Eliminate Queue Problems**: Allow users to order food online, reducing physical queuing time.

2. **Improve User Experience**: Provide an intuitive, modern interface for browsing menus and placing orders.

3. **Multiple Payment Options**: Support Cash, Wallet, and Online (UPI/Card) payment methods.

4. **Order Tracking**: Enable real-time tracking of order status from placement to delivery.

5. **Delivery Feature**: Allow food delivery to classrooms and staffrooms.

6. **Admin Management**: Provide admin panel for menu management, order processing, and user management.

7. **Digital Records**: Maintain digital records of all transactions for better accounting.

---

## 1.4 Category

**Web Application** - Full Stack Development Project

**Domain**: Food Service Management / E-Commerce

---

## 1.5 Language to be Used

| Component | Technology |
|-----------|------------|
| Frontend | HTML5, CSS3, JavaScript |
| Backend | Python 3.13 |
| Framework | Django 6.0 |
| Database | MySQL 8.0 |
| IDE | PyCharm / VS Code |

---

## 1.6 Hardware Interface

**Minimum Hardware Requirements:**

| Component | Specification |
|-----------|---------------|
| Processor | Intel Core i3 or equivalent |
| RAM | 4 GB minimum |
| Storage | 10 GB free space |
| Display | 1366 x 768 resolution |
| Network | Internet connectivity |

---

## 1.7 Software Interface

| Software | Version/Details |
|----------|-----------------|
| Operating System | Windows 10/11, Linux, macOS |
| Web Browser | Chrome, Firefox, Edge (latest versions) |
| Python | 3.10 or higher |
| MySQL Server | 8.0 or higher |
| Django | 6.0 |
| Additional Packages | django-allauth, Pillow, mysqlclient |

---

## 1.8 Description

The Smart College Canteen Management System is designed with a modular architecture consisting of the following key components:

**User Authentication Module:**
- User registration with email verification
- Login/Logout functionality
- Role-based access (Student, Staff, Admin)
- Social login options (Google, Facebook)

**Menu Management Module:**
- Dynamic menu display with categories
- Veg/Non-Veg filtering
- Search functionality
- Today's specials highlighting
- Price and preparation time display

**Cart Module:**
- Add/Remove items
- Quantity adjustment
- Real-time price calculation

**Order Module:**
- Order placement with special instructions
- Multiple delivery options (Pickup, Classroom, Staffroom)
- Order history tracking
- Reorder functionality

**Payment Module:**
- Cash at counter
- Wallet balance
- Online payment (UPI/Card simulation)
- Transaction history

---

## 1.9 Module Description

### Module 1: User Authentication
- Registration with form validation
- Secure password storage (hashed)
- Session management
- Password reset functionality

### Module 2: Menu Management
- CRUD operations for menu items
- Category management
- Image upload for items
- Availability toggle

### Module 3: Cart Management
- Session-based cart storage
- Dynamic subtotal calculation
- Cart persistence across sessions

### Module 4: Order Processing
- Token number generation
- Estimated wait time calculation
- Order status updates
- Email notifications

### Module 5: Payment Processing
- Multiple payment method support
- Wallet management
- Transaction logging
- Payment confirmation

### Module 6: Admin Dashboard
- User management
- Order management
- Menu item management
- Reports and analytics

---

## 1.10 Future Scope

1. **Mobile Application**: Develop native Android/iOS applications for better accessibility.

2. **AI-based Recommendations**: Implement machine learning to suggest items based on user preferences.

3. **Real-time Notifications**: Push notifications for order status updates.

4. **QR Code Ordering**: Enable table-side ordering using QR codes.

5. **Inventory Management**: Automatic stock tracking and alerts.

6. **Analytics Dashboard**: Detailed sales analytics and reports.

7. **Multi-branch Support**: Extend to support multiple canteen locations.

8. **Loyalty Program**: Points-based rewards system for regular customers.

---

# CHAPTER 2: SOFTWARE REQUIREMENT SPECIFICATION

## 2.1 Introduction

This chapter describes the software requirements for the Smart College Canteen Management System. It provides a detailed specification of the system's functional and non-functional requirements.

---

## 2.2 Purpose

The purpose of this SRS document is to provide a comprehensive description of the Smart College Canteen Management System. It will cover the complete system from user perspective and technical specification required for development.

---

## 2.3 Scope

The system scope includes:
- User registration and authentication
- Menu browsing with filters
- Shopping cart functionality
- Order placement and tracking
- Payment processing
- Admin management panel
- Delivery management

**Out of Scope:**
- Real payment gateway integration
- Inventory management
- Supplier management

---

## 2.4 Definitions, Acronyms, Abbreviations

| Term | Definition |
|------|------------|
| SRS | Software Requirement Specification |
| DFD | Data Flow Diagram |
| ER | Entity Relationship |
| CRUD | Create, Read, Update, Delete |
| UPI | Unified Payments Interface |
| OTP | One Time Password |
| UI | User Interface |
| API | Application Programming Interface |

---

## 2.5 Overview

The Smart College Canteen Management System consists of:
- **Frontend**: Web-based responsive interface
- **Backend**: Django-based REST APIs
- **Database**: MySQL relational database
- **Authentication**: Django authentication with django-allauth

---

## 2.6 Overall Description

The system serves three types of users:
1. **Students**: Can browse menu, place orders, make payments
2. **Staff**: Same as students with optional staff room delivery
3. **Admin**: Full system management access

---

## 2.7 Product Perspective

This is a standalone web application designed specifically for college canteen management. It integrates:
- User management system
- Menu catalog system
- Order processing system
- Payment handling system
- Notification system

---

## 2.8 Product Functions

| Function | Description |
|----------|-------------|
| User Registration | Create new user accounts |
| User Login | Authenticate existing users |
| Browse Menu | View all available food items |
| Search Items | Find items by name or category |
| Add to Cart | Select items for purchase |
| Checkout | Complete order with delivery preference |
| Make Payment | Process payment via selected method |
| Track Order | View order status |
| Manage Menu | Admin CRUD for menu items |

---

## 2.9 User Classes and Characteristics

**1. Student User**
- Primary user group
- Tech-savvy, mobile-first
- Uses system during breaks
- Needs quick ordering

**2. Staff User**
- Faculty and administrative staff
- May need delivery to staffroom
- Less frequent usage

**3. Admin User**
- Canteen manager/owner
- Full system access
- Manages menu and orders

---

## 2.10 General Constraints

1. System requires internet connectivity
2. Browser must support JavaScript
3. MySQL database required
4. Python 3.10+ environment needed

---

## 2.11 Assumptions and Dependencies

**Assumptions:**
- Users have access to internet-enabled devices
- Users have basic computer literacy
- Canteen has network infrastructure

**Dependencies:**
- Django framework
- MySQL database server
- Python runtime environment
- Web browser

---

## 2.12 Specific Requirements

### 2.12.1 Software Requirements

| Requirement | Specification |
|-------------|---------------|
| Python | Version 3.10 or higher |
| Django | Version 6.0 |
| MySQL | Version 8.0 |
| Browser | Chrome/Firefox/Edge (latest) |

### 2.12.2 Hardware Requirements

| Component | Minimum Requirement |
|-----------|---------------------|
| Processor | Intel Core i3 |
| RAM | 4 GB |
| Storage | 10 GB |
| Network | 1 Mbps internet |

### 2.12.3 Communication Interface

- HTTP/HTTPS protocol for web communication
- TCP/IP for database connectivity
- SMTP for email notifications

---

## 2.13 Functional Requirements

| FR ID | Requirement | Priority |
|-------|-------------|----------|
| FR01 | User shall be able to register | High |
| FR02 | User shall be able to login | High |
| FR03 | User shall be able to browse menu | High |
| FR04 | User shall be able to search items | Medium |
| FR05 | User shall be able to filter by veg/non-veg | Medium |
| FR06 | User shall be able to add items to cart | High |
| FR07 | User shall be able to modify cart | High |
| FR08 | User shall be able to place order | High |
| FR09 | User shall be able to make payment | High |
| FR10 | User shall be able to track order | High |
| FR11 | Admin shall be able to manage menu | High |
| FR12 | Admin shall be able to manage orders | High |

---

## 2.14 Performance Requirements

| Requirement | Specification |
|-------------|---------------|
| Response Time | < 3 seconds for page load |
| Concurrent Users | Support 100+ simultaneous users |
| Database Queries | < 100ms average query time |
| Uptime | 99% availability |

---

## 2.15 Design Constraints

1. Must be responsive (mobile-friendly)
2. Must use dark theme for UI
3. Must follow Django best practices
4. Must use MySQL as database

---

## 2.16 System Attributes

**Reliability**: System should handle errors gracefully with appropriate error messages.

**Availability**: System should be available during canteen operating hours.

**Security**: User passwords are hashed, CSRF protection enabled.

**Maintainability**: Modular code structure for easy updates.

---

## 2.17 Other Requirements

### 2.17.1 Safety Requirements
- Input validation to prevent SQL injection
- XSS protection
- Secure session handling

### 2.17.2 Security Requirements
- Password hashing using Django's built-in hasher
- CSRF token validation
- HTTPS recommended for production
- Role-based access control

---

# CHAPTER 3: SYSTEM DESIGN

## 3.1 Introduction

This chapter presents the system design including data flow diagrams, entity relationship diagrams, and system architecture.

---

## 3.2 Context Flow Design

```
[User] ----> [Canteen Management System] ----> [Database]
                      |
                      v
               [Admin Panel]
```

---

## 3.3 Data Flow Diagram

The DFD represents the flow of data through the system at various levels.

---

## 3.4 Rules Regarding DFD Constraints

1. All data flows must have a source and destination
2. All processes must have inputs and outputs
3. Data stores cannot directly connect to each other
4. External entities cannot directly connect to data stores

---

## 3.5 DFD Symbols

| Symbol | Name | Description |
|--------|------|-------------|
| ○ | Process | Transforms data |
| □ | External Entity | Source/Destination of data |
| ═ | Data Store | Storage of data |
| → | Data Flow | Movement of data |

---

## 3.6 DFD for Admin

### 3.6.1 DFD for Login
```
[Admin] --credentials--> (1.0 Validate Login) --session--> [Admin Dashboard]
```

### 3.6.2 DFD for Menu Management
```
[Admin] --menu data--> (2.0 Manage Menu) <--> [Menu Database]
```

### 3.6.3 DFD for Order Management
```
[Admin] --status update--> (3.0 Process Order) <--> [Order Database]
```

### 3.6.4 DFD for View Payment
```
[Admin] --request--> (4.0 View Payments) --payment list--> [Admin]
                           ^
                           |
                    [Payment Database]
```

### 3.6.5 DFD for View Users
```
[Admin] --request--> (5.0 View Users) --user list--> [Admin]
                           ^
                           |
                      [User Database]
```

---

## 3.7 DFD for User

### 3.7.1 DFD for Login
```
[User] --credentials--> (1.0 Authenticate) --session--> [Home Page]
                              ^
                              |
                        [User Database]
```

### 3.7.2 DFD for Register
```
[User] --registration data--> (2.0 Register) --confirmation--> [User]
                                    |
                                    v
                              [User Database]
```

### 3.7.3 DFD for View Menu
```
[User] --request--> (3.0 Fetch Menu) --menu items--> [User]
                          ^
                          |
                    [Menu Database]
```

### 3.7.4 DFD for Add to Cart
```
[User] --item selection--> (4.0 Update Cart) <--> [Session Storage]
```

### 3.7.5 DFD for Place Order
```
[User] --order details--> (5.0 Create Order) --confirmation--> [User]
                                |
                                v
                          [Order Database]
```

### 3.7.6 DFD for Make Payment
```
[User] --payment info--> (6.0 Process Payment) --receipt--> [User]
                               |
                               v
                        [Payment Database]
```

### 3.7.7 DFD for View Order History
```
[User] --request--> (7.0 Fetch Orders) --order list--> [User]
                          ^
                          |
                    [Order Database]
```

---

## 3.8 Entity Relationship Diagram (ER Diagram)

**Entities:**

1. **User**: user_id, username, email, password, role, wallet_balance
2. **Category**: category_id, name, description, is_active
3. **MenuItem**: item_id, name, price, description, image, is_available, is_vegetarian
4. **Order**: order_id, user_id, total_amount, status, delivery_type, created_at
5. **OrderItem**: id, order_id, item_id, quantity, price
6. **Payment**: payment_id, order_id, amount, method, status, transaction_id

**Relationships:**
- User (1) --- (M) Order
- Order (1) --- (M) OrderItem
- MenuItem (1) --- (M) OrderItem
- Category (1) --- (M) MenuItem
- Order (1) --- (1) Payment

---

## Database Schema

```sql
-- Users Table
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(150) UNIQUE,
    email VARCHAR(254) UNIQUE,
    password VARCHAR(128),
    role VARCHAR(20),
    wallet_balance DECIMAL(10,2)
);

-- Category Table
CREATE TABLE category (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    description TEXT,
    is_active BOOLEAN
);

-- MenuItem Table
CREATE TABLE menu_item (
    id INT PRIMARY KEY AUTO_INCREMENT,
    category_id INT FOREIGN KEY REFERENCES category(id),
    name VARCHAR(100),
    price DECIMAL(8,2),
    description TEXT,
    is_available BOOLEAN,
    is_vegetarian BOOLEAN
);

-- Order Table
CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT FOREIGN KEY REFERENCES users(id),
    token_number VARCHAR(20),
    total_amount DECIMAL(10,2),
    status VARCHAR(20),
    delivery_type VARCHAR(20),
    created_at DATETIME
);

-- OrderItem Table
CREATE TABLE order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT FOREIGN KEY REFERENCES orders(id),
    menu_item_id INT FOREIGN KEY REFERENCES menu_item(id),
    quantity INT,
    price DECIMAL(8,2)
);

-- Payment Table
CREATE TABLE payments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT FOREIGN KEY REFERENCES orders(id),
    amount DECIMAL(10,2),
    method VARCHAR(20),
    status VARCHAR(20),
    transaction_id VARCHAR(50)
);
```

---

# END OF DOCUMENT

---

**Prepared By:** [Your Name]
**Date:** February 2026
**Version:** 1.0
