# Project Report Outline

## Title
Company Selection and Job Recommendation System

## Abstract
The Company Selection and Job Recommendation System is a web-based application designed to help students and job seekers explore career opportunities. Users can create profiles, enter educational details and skills, receive job recommendations, identify missing skills, shortlist companies and track applications. The prototype uses Python, Streamlit and SQLite. A transparent skill-overlap algorithm calculates a match score between a user's profile and the skills required by each sample job.

## Problem Statement
Students and fresh graduates often find it difficult to identify suitable companies and job roles. Job information is spread across multiple platforms, and candidates may not know which skills they need to improve. The proposed system provides a single interface for profile management, job matching, company exploration and application tracking.

## Objectives
1. Build a simple and user-friendly job recommendation platform.
2. Store user and job information in an SQLite database.
3. Recommend jobs based on profile skills and interests.
4. Identify missing skills for a selected job role.
5. Help users save jobs, shortlist companies and track applications.
6. Demonstrate resume text extraction and skill detection.

## Technology Stack
- Frontend: Streamlit
- Programming language: Python
- Database: SQLite
- Password hashing: PBKDF2-HMAC-SHA256
- Resume parsing: pypdf and python-docx
- Recommendation: skill matching and percentage scoring

## Modules
1. Authentication
2. User Profile
3. Job Recommendation
4. Company Explorer
5. Skill Gap Analysis
6. Resume Analyzer
7. Saved Jobs
8. Application Tracker
9. Company Comparison
10. Demo Job Management

## Recommendation Formula
Match Score = (Matched Required Skills / Total Required Skills) × 100

## Limitations
The project uses illustrative demo listings, not live verified vacancies. The recommendation method is a baseline keyword-overlap approach. Scanned resume OCR and live job API integration are not included.

## Conclusion
The prototype demonstrates how a centralized career-support application can organize job discovery and help candidates understand skill requirements. Future work can include verified live job feeds, semantic NLP matching, role-based administration and notification services.
