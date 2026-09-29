# CultureShield AI - Product Requirements Document

## Original Problem Statement
Build a SaaS web application called "CultureShield AI" - a cybersecurity culture audit platform that helps small and medium businesses assess employees' cybersecurity awareness, behavior, and risk level through automated audits and AI-powered reports.

## User Personas
- **HR Managers**: Need to assess employee security awareness for compliance
- **IT Security Officers**: Require visibility into human cyber risks
- **Business Owners**: Want to understand and improve organizational security culture

## Core Requirements (Static)
1. Company registration and authentication (JWT)
2. Employee management with survey invitations
3. Cybersecurity culture survey (18 questions across 3 categories)
4. Score calculation engine (Awareness, Behavior, Reporting)
5. Dashboard with visualizations (charts, heatmaps, department breakdown)
6. AI-powered audit report generation (GPT-5.2)
7. PDF report download

## What's Been Implemented (March 2026)

### Phase 1 - MVP
- ✅ Landing page with hero section, features, CTA
- ✅ Company registration and login (JWT authentication)
- ✅ Company dashboard with CultureShield Score
- ✅ Employee management (add, view, delete, copy survey links)
- ✅ Employee survey page with 18 questions
- ✅ Basic score calculation engine
- ✅ AI report generation using GPT-5.2
- ✅ PDF report download

### Phase 2 - Enhanced Risk Scoring (NEW)
- ✅ **Weighted Scoring System**: Risk-weighted calculations with multipliers for critical behaviors
- ✅ **Critical Risk Flag Detection**: Automatic detection of dangerous behaviors:
  - Password Reuse (q5) - 2.5x multiplier
  - Phishing Susceptibility (q11) - 2.5x multiplier  
  - Credential Sharing (q17) - 2.5x multiplier
  - Unsecured Network Usage (q9) - 2.0x multiplier
  - No Email Verification (q12) - 2.0x multiplier
- ✅ **Risk Profiles/Personas**: 8 distinct profiles (Critical Risk, High Risk, Phishing Target, Password Liability, Policy Violator, Device Risk, Silent Observer, Security Aware)
- ✅ **Vulnerability Index**: Company-wide metric (0-100) measuring overall security posture
- ✅ **High-Risk Employee Identification**: Automatic flagging with top 10 list
- ✅ **Behavioral Red Flags Aggregation**: Company-wide view of critical issues
- ✅ **Enhanced Risk Levels**: 6-tier system (Low, Low-Medium, Medium, Medium-High, High, Critical)
- ✅ **Risk Distribution Chart**: Visual breakdown of employee risk levels
- ✅ **Enhanced Heatmap**: 7 risk categories including social engineering and credential hygiene

### Phase 3 - Analytics & Bulk Import (NEW)
- ✅ **Historical Trend Analysis**:
  - Weekly trends (last 4 weeks) with score tracking
  - Monthly trends (last 6 months) for long-term analysis
  - Score change indicators (weekly/monthly)
  - Trend direction detection (improving/declining/stable)
  - AI-generated insights and recommendations
- ✅ **Interactive Trend Charts**:
  - Area charts for overall score progression
  - Line charts for category breakdown (Awareness, Behavior, Reporting)
  - Bar charts for survey participation over time
- ✅ **Bulk CSV Import**:
  - Upload CSV files with employee data
  - Required columns: name, email
  - Optional column: department
  - Validation for duplicate emails
  - Error reporting with row-by-row details
  - Maximum 500 employees per import
  - Downloadable CSV template

### Phase 4 - Paystack Billing System (NEW)
- ✅ **Public Pricing Experience**:
  - Public `/pricing` page with Free, Starter, Business, Pro, and Pay Per Audit plans
  - NGN pricing display with plan features and trial messaging
- ✅ **Authenticated Billing Portal**:
  - `/billing` route with Plans, Portal, and Intelligence tabs
  - Current plan, next billing date, usage snapshot, coupon input, invoices, and payment methods
  - In-app customer billing portal endpoint: `GET /api/billing/portal`
- ✅ **Paystack Checkout Integration**:
  - Hosted checkout initialization for recurring subscriptions and one-time audit purchases
  - Payment callback page and verification flow scaffolded for redirect-based completion
  - Pending transaction storage and MOCKED abandoned-cart reminder logging
- ✅ **Feature Gating & Limits**:
  - Free plan auto-created at registration
  - Free plan limited to 5 employees
  - AI report generation blocked for free plan until paid plan or one-time audit purchase
  - Billing-aware redirect from Reports page to billing when gated
- ✅ **Billing Intelligence**:
  - Admin billing dashboard with MRR, ARR, churn, ARPU, delinquency, revenue by plan, and at-risk customers
  - Churn heuristics and retention workflow logging in backend
- ✅ **Billing Notifications**:
  - All billing emails/notifications are currently **MOCKED** to console/database logs

### Phase 5 - Auth Stability Hardening (NEW)
- ✅ Added safer frontend auth request handling for registration, login, and token verification
- ✅ Added retry logic for transient network failures during auth requests
- ✅ Cleared frontend cache / restarted frontend to resolve stale bundle issues affecting account creation
- ✅ Verified registration and login end-to-end after fix

### Phase 6 - Resend Email Notifications (NEW)
- ✅ Integrated Resend in the backend with `RESEND_API_KEY` and `SENDER_EMAIL`
- ✅ Enabled transactional email attempts for:
  - Welcome email on company registration
  - Survey invite email on employee creation / bulk import
  - Survey completion alert to company admins
  - Report-ready email after audit generation
  - Billing event emails for payment/plan notifications
- ✅ Implemented graceful failure handling so email delivery issues do not break app flows
- ✅ Added sanitized email error handling to avoid leaking sensitive recipient details in logs
- ⚠️ Current sender uses `onboarding@resend.dev`, so Resend sandbox restrictions apply until a sending domain is verified

### Phase 7 - Email Activity Dashboard + Downloadable App (NEW)
- ✅ Added `email_events` logging for all transactional emails with status, type, provider response, metadata, and company scope
- ✅ Added admin email history APIs:
  - `GET /api/billing/admin/email-activity`
  - `GET /api/billing/admin/email-activity/export`
- ✅ Added email activity/history panel to the billing intelligence dashboard with summary cards and CSV export
- ✅ Made the app downloadable/installable from the site as a PWA-style web app:
  - `manifest.json`
  - `service-worker.js`
  - Download App buttons on landing page and billing dashboard
- ✅ Added graceful install fallback messaging for browsers that do not expose the install prompt
- ✅ Fixed dialog accessibility warning in employee management by adding dialog descriptions

### Phase 8 - Billing Scope + Account Switching Fixes (NEW)
- ✅ Fixed billing intelligence scoping so company admins only see metrics for their own company account
- ✅ Fixed false at-risk entries for free/no-activity accounts by excluding free-plan churn scoring from risk calculations
- ✅ Fixed account switching/login bleed issue caused by cached authenticated GET responses in the service worker
- ✅ Updated service worker caching to avoid `/api` and authenticated requests entirely
- ✅ Added client-side cache clearing on login/logout and safer token verification to prevent stale user state
- ✅ Verified account switching end-to-end across two different accounts in the same browser session

### Phase 9 - MFA + Password Reset Security (NEW)
- ✅ Added secure MFA for company admin accounts using TOTP authenticator apps
- ✅ MFA setup flow now supports:
  - QR code generation
  - Manual setup key
  - 8 one-time backup/recovery codes
  - Encrypted MFA secret storage in MongoDB
- ✅ MFA login flow now supports:
  - Email + password first step
  - MFA challenge token
  - TOTP verification or backup-code verification
  - Enable / disable MFA from security settings
- ✅ Added password reset system with:
  - `POST /api/auth/forgot-password`
  - `GET /api/auth/reset-password/validate`
  - `POST /api/auth/reset-password`
  - 20-minute single-use reset tokens
  - Resend email integration for reset emails
- ✅ Added password strength validation:
  - 10+ characters
  - uppercase, lowercase, number, special character
- ✅ Added auth event logging and login/MFA rate limiting (5 failed attempts / 15 minutes)
- ✅ Registration now redirects admins to security settings for MFA onboarding

### Phase 10 - Mobile Layout Hardening (NEW)
- ✅ Fixed mobile landing-page top overlap issue by making the nav wrap correctly and hiding the desktop-style install CTA on small screens
- ✅ Added `MobileAppNav` for authenticated mobile layouts
- ✅ Hid fixed desktop sidebars on mobile across dashboard, employees, analytics, reports, and billing pages
- ✅ Adjusted dashboard header action buttons to wrap cleanly on mobile

### Phase 11 - Trusted Devices / Active Sessions (NEW)
- ✅ Added server-side auth session tracking with session IDs embedded in JWTs
- ✅ Sessions are now created on:
  - registration
  - password login
  - MFA verification
- ✅ Added session-management APIs:
  - `GET /api/auth/sessions`
  - `POST /api/auth/logout`
  - `POST /api/auth/sessions/{session_id}/revoke`
  - `POST /api/auth/sessions/revoke-all`
- ✅ Added token invalidation tied to revoked sessions in `get_current_company()`
- ✅ Password reset now revokes all existing sessions for the account
- ✅ Added Trusted devices & active sessions panel to Security Settings with:
  - current session badge
  - device/browser/OS/IP metadata
  - MFA-verified vs password-only badges
  - risk flags (`new-location`, `password-only`)
  - revoke single session / revoke all other sessions controls

### Phase 12 - Phishing Simulation MVP (NEW)
- ✅ Added a polished phishing simulation module with:
  - campaign creation UI
  - employee targeting
  - reusable phishing templates (`password_reset_urgent`, `invoice_review`, `shared_document`)
  - draft or immediate-send campaign flow
- ✅ Added backend phishing APIs:
  - `GET /api/phishing/templates`
  - `GET /api/phishing/campaigns`
  - `POST /api/phishing/campaigns`
  - `GET /api/phishing/campaigns/{id}`
  - `POST /api/phishing/campaigns/{id}/send`
  - `GET /api/phishing/simulations/{token}`
  - `POST /api/phishing/simulations/{token}/report`
  - `GET /api/phishing/track/open/{token}`
- ✅ Added recipient-level outcome tracking:
  - delivery status
  - open tracking
  - click tracking
  - report tracking
- ✅ Added safe public training landing page at `/phishing/simulation/:token`
- ✅ Added results dashboard with employee-level outcomes and campaign metrics (targets, clicks, reports)
- ✅ Added phishing navigation to desktop sidebar and mobile navigation
- ⚠️ Resend sandbox restrictions still apply for non-verified recipients, but campaign creation/results/tracking continue to work correctly

### Phase 12.1 - Phishing Feature Pricing Alignment (NEW)
- ✅ Updated pricing plans so phishing simulations are positioned correctly:
  - Free: no phishing
  - Starter: no phishing
  - Business: includes `Phishing simulations`
  - Pro: includes `Advanced phishing simulations`
- ✅ Added backend gating so phishing simulation management is accessible only on Business and Pro plans
- ✅ Added upgrade-required UI state on `/phishing` for non-entitled accounts
- ✅ Updated pricing page assurance copy to mention Business/Pro phishing simulation drills

### Phase 13 - Standards-Aligned Scoring & Reporting (NEW)
- ✅ Reworked the cybersecurity culture scoring model to align with ISO/IEC 27001:2022 awareness and human-security controls plus NIST CSF principles as **guidance only**
- ✅ Added a 5-level maturity model:
  - Initial
  - Developing
  - Defined
  - Managed
  - Adaptive
- ✅ Added four framework-aligned human-risk domains:
  - Governance & Awareness
  - Protective Behavior
  - Threat Recognition & Verification
  - Reporting & Response Readiness
- ✅ Each domain now includes:
  - ISO reference
  - NIST reference
  - maturity level
  - domain score
- ✅ Company-level dashboard scoring now blends:
  - standards-aligned domain weighting
  - critical/high risk-flag penalties
  - phishing simulation evidence modifier when available
- ✅ Added standards-aware dashboard outputs:
  - `maturity_level`
  - `maturity_summary`
  - `framework_note`
  - `aligned_domains`
  - `phishing_program`
- ✅ Audit reports now include support for:
  - framework alignment notice
  - maturity assessment
  - control-domain scores
  - phishing evidence findings
  - standards alignment mapping
- ✅ Report detail UI updated to render the new sections
- ✅ Dashboard UI now shows the maturity badge and maturity summary prominently

### Phase 14 - Board-Ready Standards Summary (NEW)
- ✅ Added dedicated protected route: `/standards-summary`
- ✅ Added executive-ready leadership page with:
  - overall score card
  - maturity snapshot card
  - participation card
  - phishing posture card
- ✅ Added standards-aligned control-domain section with ISO/NIST references for all four human-risk domains
- ✅ Added board action priorities derived from lowest-scoring domains and phishing evidence status
- ✅ Added top human-risk signals, department spotlight, phishing evidence, and report-readiness sections
- ✅ Added print-friendly layout and `Print summary` action for leadership reviews
- ✅ Added navigation entry points:
  - dashboard sidebar link
  - dashboard header button
  - mobile nav `Board` item

### Phase 15 - Board Summary PDF Export (NEW)
- ✅ Added authenticated backend endpoint: `GET /api/board-summary/pdf`
- ✅ Implemented one-click PDF export for the board summary with:
  - executive snapshot
  - standards notice
  - control-domain scores
  - board action priorities
  - top human-risk signals
  - department spotlight
  - phishing evidence
- ✅ Added frontend `Download PDF` action to `/standards-summary`
- ✅ Preserved existing `Print summary` action with no regression

## Architecture
- **Frontend**: React 19 + Tailwind CSS + Shadcn/UI + Recharts + Framer Motion
- **Backend**: FastAPI + Motor (MongoDB async driver)
- **Database**: MongoDB
- **AI Integration**: OpenAI GPT-5.2 via emergentintegrations library
- **PDF Generation**: FPDF2 with text sanitization for unicode support
- **Billing Integration**: Paystack hosted checkout + webhook-ready billing routes + MongoDB billing collections
- **Email Integration**: Resend transactional email service with async fire-and-forget delivery attempts
- **Installability**: PWA manifest + service worker + browser install/download entry points
- **Cache Safety**: Service worker now bypasses API/authenticated traffic to prevent stale cross-account data
- **Auth Security**: TOTP MFA + encrypted secret storage + password reset tokens + rate limiting + auth event logs
- **Session Security**: Server-side active session tracking + device metadata + token revocation
- **Phishing Simulation**: campaign templates + safe tracked landing pages + recipient outcome analytics
- **Standards Alignment**: ISO/IEC 27001 + NIST CSF guidance mapping + maturity-based human-risk scoring
- **Executive Reporting**: Dedicated board-summary view for leadership-ready standards snapshots
- **Board Exporting**: Downloadable executive PDF summary for leadership sharing

## API Endpoints
- `POST /api/auth/register` - Company registration
- `POST /api/auth/login` - Company login
- `GET /api/auth/me` - Get current company
- `POST /api/employees` - Add single employee
- `GET /api/employees` - List all employees
- `DELETE /api/employees/{id}` - Delete employee
- `POST /api/employees/bulk-import` - Bulk CSV import
- `GET /api/employees/csv-template` - Get CSV format
- `GET /api/survey/questions` - Get all survey questions
- `GET /api/survey/employee/{id}` - Get employee for survey
- `POST /api/survey/submit/{id}` - Submit survey responses
- `GET /api/dashboard/stats` - Get dashboard statistics
- `GET /api/analytics/trends` - Get historical trends
- `POST /api/reports/generate` - Generate AI report
- `GET /api/reports` - List all reports
- `GET /api/reports/{id}` - Get report details
- `GET /api/reports/{id}/pdf` - Download PDF report
- `GET /api/billing/plans` - Get all pricing plans
- `POST /api/billing/checkout/subscribe` - Initialize recurring plan checkout
- `POST /api/billing/checkout/audit` - Initialize one-time audit checkout
- `GET /api/billing/checkout/verify/{reference}` - Verify Paystack payment redirect
- `GET /api/billing/info` - Get customer billing portal data
- `GET /api/billing/portal` - Get in-app billing portal URL
- `GET /api/billing/admin/dashboard` - Get billing intelligence metrics
- `GET /api/billing/access/{feature}` - Check feature access by plan
- `GET /api/billing/admin/email-activity` - Get company email history + summary
- `GET /api/billing/admin/email-activity/export` - Download email history CSV
- `POST /api/auth/mfa/setup/init` - Start MFA setup and return QR/manual key/backup codes
- `POST /api/auth/mfa/setup/confirm` - Confirm MFA setup with TOTP code
- `POST /api/auth/mfa/verify-login` - Complete MFA login challenge
- `GET /api/auth/mfa/status` - Fetch current MFA status
- `POST /api/auth/mfa/disable` - Disable MFA with password + TOTP/backup code
- `POST /api/auth/forgot-password` - Request password reset link
- `GET /api/auth/reset-password/validate` - Validate reset token
- `POST /api/auth/reset-password` - Complete password reset
- `GET /api/auth/sessions` - List active sessions / trusted devices
- `POST /api/auth/logout` - Revoke current session
- `POST /api/auth/sessions/{session_id}/revoke` - Revoke a chosen session
- `POST /api/auth/sessions/revoke-all` - Revoke all other sessions
- `GET /api/phishing/templates` - List available phishing templates
- `GET /api/phishing/campaigns` - List phishing campaigns with aggregated metrics
- `POST /api/phishing/campaigns` - Create draft or send phishing campaign
- `GET /api/phishing/campaigns/{id}` - Get recipient-level campaign outcomes
- `POST /api/phishing/campaigns/{id}/send` - Send a draft campaign
- `GET /api/phishing/simulations/{token}` - Safe public training landing + click tracking
- `POST /api/phishing/simulations/{token}/report` - Log reported-phishing action
- `GET /api/phishing/track/open/{token}` - Open-tracking pixel endpoint
- `GET /api/dashboard/stats` - Now includes maturity + standards alignment outputs

## Prioritized Backlog

### P0 (Critical) - DONE
- Company auth flow ✅
- Survey system ✅
- Dashboard scores ✅
- Report generation ✅
- Enhanced risk scoring ✅
- Historical trend analysis ✅
- Bulk CSV import ✅
- Paystack billing system ✅

### P1 (High Priority) - Future
- Verify a sending domain in Resend and move from sandbox/testing-mode delivery to full recipient coverage
- Add session-refresh resilience around Paystack callback return flow
- Add richer phishing features (scheduling, cloned scenarios, department segmentation) if desired
- Expand PWA install/offline support beyond shell caching if needed
- Add role-aware platform-owner analytics view separately from company-admin billing intelligence if needed
- Add device/session management UI for admins (optional future hardening)
- Add department-level maturity trends and standards alignment history over time
- Add benchmarking and board trend views across reporting periods
- Add period-over-period PDF packs and multi-board reporting bundles if needed

### P2 (Medium Priority) - Future
- Custom survey questions
- Multi-language support
- White-label branding
- Export data to Excel
- Refactor large backend modules out of `server.py`

## Next Tasks
1. Verify a Resend sending domain so emails can reach non-verified recipients in production
2. Optionally expand phishing simulations with scheduling and more scenario types
3. Refactor more backend domains out of `server.py`
