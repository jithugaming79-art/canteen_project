## 2.1 Introduction
The Smart College Canteen Management System (CampusBites) is a web-based application developed to modernize the traditional food ordering process in educational institutions. This chapter provides a detailed specification of the requirements for the system, covering everything from the purpose and scope to specific technical requirements and constraints. It serves as a foundational document for the development, testing, and deployment phases of the project.

## 2.2 Purpose
The primary purpose of this specification is to define the functional and non-functional requirements of the Smart College Canteen Management System. It aims to eliminate long queues, improve order accuracy, enable cashless transactions, and provide real-time order tracking. This document provides a clear understanding of the system's goals and functionality for developers, stakeholders, and users, ensuring that the final product meets the needs of the college community.

## 2.3 scope
The scope of the project includes the development of a responsive web application for students, staff, and canteen administrators. Key features include user registration and authentication, a dynamic menu with filtering options, a shopping cart system, order placement with delivery preferences (pickup, classroom, or staffroom), a digital wallet for payments, QR code generation for order verification, and an admin dashboard for managing menu items and processing orders. The system focuses on a single canteen location and does not include real-world payment gateway integration or inventory management.

## 2.4 Defination, Acronyms, Abbreviation
- **SRS**: Software Requirement Specification
- **DFD**: Data Flow Diagram
- **ER**: Entity Relationship
- **CRUD**: Create, Read, Update, Delete
- **UPI**: Unified Payments Interface (Simulated)
- **QR**: Quick Response (code)
- **UI**: User Interface
- **MVT**: Model-View-Template (Architecture)
- **ORM**: Object-Relational Mapping
- **Veg**: Vegetarian
- **Non-Veg**: Non-Vegetarian
- **Admin**: Administrator
- **CSRF**: Cross-Site Request Forgery (Security)
- **Wallet**: Virtual balance for transactions
- **Cart**: Temporary storage for items before ordering

## 2.5 Overview
The Smart College Canteen Management System is structured to provide a seamless interaction between three primary user groups: Customers (Students/Staff), Kitchen Staff, and Administrators. The system is built using the Django framework with a MySQL database. It provides a front-end interface for browsing and ordering, and a back-end admin panel for management. This chapter outlines the detailed requirements necessary to build, maintain, and secure this ecosystem.

## 2.6 Overal Description
The system is a standalone web application designed specifically for college canteens. It replaces manual, paper-based processes with a digital platform. Users can access the system via any modern web browser on smartphones or laptops. It handles the complete lifecycle of a food order, from browsing the digital menu and selecting items to secure payment and real-time status updates until the order is collected or delivered to a specified campus location.

## 2.7 Productive Perspective
This system is part of a larger push toward campus digitalization. It integrates multiple sub-systems including:
- **User Management**: Handling profiles and role-based access.
- **Menu System**: Providing dynamic catalog management.
- **Transaction System**: Managing the digital wallet and simulated payments.
- **Order Queue**: Organizing kitchen operations and fulfillment.
- **Notification System**: Communicating status updates via the web UI and email.

## 2.8 Product Function
Major functions of the product include:
- User registration with role selection (Student/Teacher).
- Login via credentials or Social Media (Google/Facebook).
- Browsing the menu with category and dietary filters (Veg/Non-Veg).
- Adding items to a persistent shopping cart with custom instructions.
- Placing orders with specific delivery locations (Classrooms/Staffrooms).
- Cashless payments using a built-in wallet system.
- Real-time order status tracking with Token numbers and QR codes.
- Managing menu items, categories, and order fulfillment via Admin Dashboard.
- User review and rating system for quality feedback.

## 2.9 User classes and Characteristics
- **Student User**: Primary user class, frequent users, tech-savvy, uses mobile devices, needs fast ordering.
- **Staff User**: Faculty and administrative staff, uses laptops/mobiles, requires staffroom delivery.
- **Admin User**: Canteen managers/owners, manages menu items, prices, and systems access.
- **Kitchen Staff**: Personnel responsible for food prep, updates order status in real-time.

## 2.10 Genral Constraints
- Requires stable internet connectivity for all operations.
- Must be accessed through modern web browsers with JavaScript enabled.
- Limited to single-language (English) support in the current version.
- Data storage is constrained by the MySQL 8.0 environment.
- Responsive design must accommodate screen sizes from mobile to desktop.
- Orders can only be processed during canteen operational hours.

## 2.11 Assumptions and Dependensies
- **Assumptions**: Users have basic computer literacy; users have valid email IDs for registration; the canteen has a dedicated tablet or computer for the kitchen display.
- **Dependensies**: Relies on the Django 6.0 framework; depends on MySQL 8.0 database; requires Python 3.10+ runtime; depends on third-party libraries for QR code generation and social authentication.

## 2.12 Specific Requirements
The system must adhere to precise technical specifications to ensure compatibility and performance across various devices and environments.

### 2.12.1 softtware Requirements
- **Operating System**: Windows 10/11, Linux, or macOS.
- **Language**: Python 3.13.
- **Framework**: Django 6.0.
- **Database**: MySQL 8.0.
- **Web Browser**: Chrome 90+, Firefox 88+, Edge 90+.
- **Libraries**: django-allauth, Pillow, mysqlclient, qrcode.

### 2.12.2 Hardware Requirements
- **Server**: Intel Core i3 (Minimum), 4GB RAM, 10GB free disk space.
- **Client**: Any smartphone or laptop with internet access.
- **Kitchen Display**: A tablet with a minimum 10-inch screen for easy visibility.
- **Network**: Minimum 2 Mbps for users, 10 Mbps for the server.

### 2.12.3 Communication Interface
- **Protocol**: HTTP/HTTPS for web traffic.
- **Data Exchange**: JSON format for internal API communication.
- **Notifications**: SMTP protocol for email delivery.
- **Database Connection**: TCP/IP for MySQL connectivity.

## 2.13 Functional Requirements
The system shall provide high-priority functions including:
- Secure account creation and login.
- Dynamic menu browsing with search and category filters.
- Cart operations including adding, updating, and removing items.
- Order processing with unique token and QR code generation.
- Wallet balance management and transaction logging.
- Role-based dashboard views for users and administrators.
- Status update mechanism for orders (Preparing, Ready, etc.).

## 2.14 Performance Requirements
- **Response Time**: Home page should load under 2 seconds.
- **Throughput**: Support 200+ concurrent users with no lag.
- **Availability**: 99% uptime during canteen operating hours.
- **Accuracy**: 100% accuracy in financial transaction logging.
- **Storage**: Scalable database to handle up to 5,000 users and 50,000 historical orders.

## 2.15 Design Contraints
- The UI must follow a professional dark theme with glassmorphism styles.
- The application must strictly follow the Model-View-Template (MVT) architecture.
- All code must adhere to PEP 8 standards for Python development.
- The database schema must be normalized to at least 3NF.
- All sensitive operations must be protected by CSRF tokens.

## 2.16 System Attributes
- **Reliability**: Graceful handling of errors with user-friendly alerts.
- **Security**: Password hashing and role-based access control.
- **Maintainability**: Modular code divided into specific Django apps.
- **Usability**: Intuitive design requiring zero user training.
- **Portability**: Codebase runnable on various operating systems.

## 2.17 Other Requirements
Supplementary requirements to ensure the overall quality and safety of the system.

### 2.17.1 Safety Requirments
- Input validation on all forms to prevent SQL injection and XSS.
- Automatic session timeout after 24 hours of inactivity.
- Detailed logging of all data modifications for audit trails.
- Ensuring menu items have accurate descriptions to prevent allergen issues.

### 2.17.2 Security Requirments
- Encryption of sensitive data in transit (HTTPS).
- Secure storage of user passwords using PBKDF2 hashing.
- Role-based permissions to prevent unauthorized access to admin features.
- Protection against common web vulnerabilities via Django's security middleware.
