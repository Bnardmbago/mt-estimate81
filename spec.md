# AI Driven Estimate Automated System — Simplified Specification

> **Currency**: All costs and financial values are in Japanese Yen (JPY).  
> **Version**: 1.0 Simplified  
> **Relationship**: Simplified variant of the main product specification (`../spec.md`).

## 1. Overview

The AI Driven Estimate Automated System is a simple internal web application that helps generate software project estimates from client requirements.

The system uses AI to read uploaded documents or form inputs, extract requirements, and calculate estimated effort, schedule, and cost in Japanese Yen.

The main goal is to reduce manual estimation work while keeping the calculation clear, editable, and explainable.

## 2. Main Users

- Sales / Proposal Team
- Project Manager
- Business Analyst
- Management Reviewer

## 3. Core Workflow

1. User creates a new estimate.
2. User enters project information using a form.
3. User may upload requirement documents.
4. AI extracts requirements and assumptions.
5. User reviews and edits extracted information.
6. System calculates effort, NRC, and RC.
7. User exports the result as PDF, Excel, or Markdown.

## 4. Input Methods

The system must support:

- Estimation form only
- Document upload only
- Form plus document upload

Supported files:

- PDF
- Word / DOCX
- Excel
- Markdown
- Text file

## 5. Key Features

### 5.1 Project Information Form

Capture basic project details:

- Project name
- Client name
- Project overview
- System type
- Scope included
- Scope excluded
- Main features
- Number of users
- Integrations
- Data complexity
- Security or compliance needs
- Preferred delivery date
- Delivery model: Japan, offshore, or hybrid
- Maintenance requirement

### 5.2 AI Requirement Extraction

AI should extract:

- Functional requirements
- Non-functional requirements
- User roles
- Modules
- External systems
- Risks
- Missing or unclear items

AI output must be reviewable and editable before estimation.

### 5.3 Estimate Calculation

The system calculates:

- Effort in person-hours
- Effort in person-days
- Effort by phase
- Effort by role
- Estimated duration
- NRC: Non-Recurring Cost
- RC: Recurring Cost
- Total first-year cost

### 5.4 Cost Master Settings

Admin can maintain:

- Role rate per hour or day
- Productivity assumptions
- Phase percentage
- Contingency percentage
- Overhead percentage
- Monthly recurring cost items
- Tax setting if needed
- Version history of rate cards

## 6. Cost Calculation

### 6.1 Basic Effort Formula

```text
Base Effort = Estimated Size × Productivity Factor
```

Example:

```text
Base Effort = Function Points × Hours per Function Point
```

Alternative simple formula:

```text
Base Effort = Number of Features × Average Hours per Feature
```

### 6.2 Phase Effort Breakdown

```text
Phase Effort = Total Effort × Phase Percentage
```

Example phase allocation:

| Phase       | Percentage |
| ----------- | ---------: |
| Requirement |        10% |
| Design      |        15% |
| Development |        40% |
| Testing     |        25% |
| Deployment  |        10% |

### 6.3 Role Cost Calculation

```text
Role Cost = Role Effort Hours × Role Hourly Rate
```

Example:

| Role      | Effort Hours | Rate / Hour |       Cost |
| --------- | -----------: | ----------: | ---------: |
| PM        |           80 |      ¥8,000 |   ¥640,000 |
| Developer |          400 |      ¥6,000 | ¥2,400,000 |
| QA        |          120 |      ¥5,000 |   ¥600,000 |

### 6.4 NRC Calculation

NRC means one-time project cost.

```text
NRC = Labor Cost + Setup Cost + Tooling Cost + Infrastructure Setup + Contingency + Overhead
```

Detailed formula:

```text
Labor Cost = Sum of all Role Costs

Contingency = Labor Cost × Contingency Rate

Overhead = Labor Cost × Overhead Rate

NRC = Labor Cost
    + Initial Infrastructure Setup Cost
    + Initial Tooling Cost
    + Third-party Setup Cost
    + Contingency
    + Overhead
```

Example:

```text
Labor Cost = ¥3,640,000
Setup Cost = ¥300,000
Tooling Cost = ¥100,000
Contingency 15% = ¥546,000
Overhead 10% = ¥364,000

NRC = ¥4,950,000
```

### 6.5 RC Calculation

RC means recurring monthly or yearly cost after delivery.

```text
Monthly RC = Hosting + Maintenance + Support + License + Monitoring + Backup + Security
```

Detailed formula:

```text
Monthly Maintenance Cost = Monthly Support Hours × Support Hourly Rate

Monthly RC = Cloud Hosting
           + Maintenance Cost
           + Software Licenses
           + Monitoring
           + Backup
           + Security
           + Other Monthly Costs
```

Annual RC:

```text
Annual RC = Monthly RC × 12
```

Example:

```text
Hosting = ¥50,000 / month
Maintenance = ¥200,000 / month
License = ¥30,000 / month
Monitoring = ¥20,000 / month

Monthly RC = ¥300,000
Annual RC = ¥3,600,000
```

### 6.6 Total First-Year Cost

```text
First Year Cost = NRC + Annual RC
```

Example:

```text
NRC = ¥4,950,000
Annual RC = ¥3,600,000

First Year Cost = ¥8,550,000
```

## 7. Output Report

The estimate report must include:

- Project summary
- Input assumptions
- Extracted requirements
- Effort estimate
- Phase breakdown
- Role breakdown
- NRC breakdown
- RC monthly breakdown
- First-year total cost
- Risk notes
- AI confidence notes
- Version of rate card used

## 8. Admin Functions

Admin can manage:

- Users
- Role rates
- Cost assumptions
- Templates
- Estimation formulas
- Export format
- Past estimates
- Actual cost feedback

## 9. Accuracy Feedback

After project completion, user can enter:

- Actual effort
- Actual duration
- Actual NRC
- Actual RC
- Notes about variance

System compares estimate vs actual and stores lessons for future calibration.

## 10. Non-Functional Requirements

- Internal system first
- Simple web UI
- Secure login
- Role-based access
- Audit log for estimate changes
- All costs in JPY
- Export to PDF and Excel
- Processing target: under 2 minutes for normal documents
- Estimation target: under 30 seconds after data extraction

## 11. Suggested Simple Technology Stack

Use a simple stack selected by the development team.

Recommended:

- Frontend: Next.js / React
- Backend: Next.js API or FastAPI
- Database: PostgreSQL
- File Storage: Google Cloud Storage or local storage for internal use
- AI API: OpenAI, Gemini, Claude, or equivalent
- Export: PDF and Excel generator
- Deployment: Docker on GCP VM

## 12. MVP Scope

### Included in MVP

- Login
- Create estimate
- Project information form
- Upload PDF / DOCX / Excel / TXT / Markdown
- AI requirement extraction
- Editable extracted requirements
- Basic effort calculation
- NRC calculation
- RC calculation
- PDF / Excel export
- Admin rate card settings

### Excluded from MVP

- Complex function point automation
- Full JFPUG / COSMIC compliance
- Advanced machine learning model training
- Public SaaS multi-tenant billing
- Complex Gantt chart planning
- Automatic government-standard estimation

## 13. Success Criteria

- User can generate an estimate from form input.
- User can generate an estimate from uploaded documents.
- NRC and RC are clearly calculated.
- Cost assumptions are editable.
- Estimate report can be exported.
- Management can understand how the cost was calculated.

## 14. Document Control

| Field             | Value                                      |
| ----------------- | ------------------------------------------ |
| Document Owner    | Product Owner                              |
| Currency          | Japanese Yen (JPY)                         |
| Version           | 1.0 Simplified                             |
| Review Frequency  | When estimation rules or rates change      |
