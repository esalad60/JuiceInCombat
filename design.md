# System Blueprint (_a.k.a._ "Design Doc")

## TNPG: JuiceInCombat
## project: Juice in Combat
## Target ship date: {2026-06-05}

---

#### roster:


| Name | Email | Primary Role | Secondary Role |
|---|---|---|---|
| | | | |
| | | | |
Eviss Wu | evissw@nycstudents.net | Server-side Developer | Backend Developer
Lucas Zheng | lucasz12@nycstudents.net | Graphics Developer | Front-end Developer
Ethan Saldanha | ethans201@nycstudents.net | Project Manager | Backend Developer
| | | | |

---


# Summary
JuiceInCombat [name subject to change] is a 3D turn based tabletop strategy game developed by JuiceInCombat. The game revolves around building (or utilizing preplaced) economy and production buildings to create troops to destroy the enemy team. The game will feature researching to unlock powerful troops and better economy buildings, different terrain tiles influencing unit stats, and a wide variety of army configurations to play from. The games are 1v1s and players win by capturing the enemy capital. 

## Problem Being Solved
Lack of a properly balanced tabletop turn-based strategy game with a good feel

## Target Users

Who will use this system?

- People that want to have fun!!!
- People who are bored
- People who like fair TBS games


## Why This Project Matters

Poeple want to have fun. People desire well-built turn-based strategy games. 

---

# Minimum Viable Product (MVP) Scope
- At least one working 3D map and rendering
- Five or more different units, including a basic supply unit
- Working income/building models and implementation
- Some terrain (even if just plains)
- A working room-based matchmaking system
- A rudimentary research tree for unlocking said units

## Core Features (Required for Final Submission)
Features that **must** be completed:
1. P2P Turn-based
1. Rendering our game's frontend
1. Combat and Movement System
1. Buildings
1. At least two armies

## Stretch Features (Only if MVP is Complete)
1. Even more balancing
1. Accounts
1. Fleshed out research trees and units
1. Multiple maps
1. Fleshed out terrains/generation

## Explicit Non-Goals

Features intentionally excluded:
- More than one player on each team in combat
- AI-controlled armies
- A campaign of sorts

---

# Technology Stack

| Layer | Selected Tool |
|---|---|
| Backend Framework | Flask |
| Frontend Framework | tailwind |
| Database | SQLite |
| Authentication |  |
| ORM / DB Library | optionally SQLAlchemy; initiate clearance protocol if interested |

## Why This Stack Was Chosen
{your summary/recap of team discussions here}

---

# Team Ownership Plan

Each member must own meaningful deliverables.

| Team Member | Primary Ownership | Secondary Ownership | Specific Deliverables |
|---|---|---|---|
| | | | |
| | | | |
| | | | |
| | | | |

---

# Component map

{Insert your mermaid(or equivalent)-generated diagram here}

# Site map

{Insert your mermaid(or equivalent)-generated diagram here}
eg...
```
Landing Page
   ↓
Login / Register
   ↓
Dashboard
   ├── Feature A
   ├── Feature B
   └── Profile
```

## Key User Stories
### eg0
As a __________, I want to __________ so that...

### eg1
As a __________, I want to __________ so that...

### eg2
As a __________, I want to __________ so that...



# Database Design

{Insert your table/document organizational structure here}


# Testing Plan
{Delineate here your plan for testing each component}

# Timeline
## Week 1 Goals:
## Week 2 Goals:
## Week 3 Goals:
## Internal Deadlines:
{List milestones your team has identified, in the order they must be completed. Set a target completion date for each.}


# Completion Criteria (_a.k.a._ "Definition of 'Done'")
Project is considered complete when all of the following are true:
1.
1.
1.

# Open Questions
{Delineate anything undecided here}

# Appendix
{Any relevant info that is useful but would have interrupted narrative flow above, or cluttered the information portrayed}

# Other
{Put here anything that did not sensibly fit under above headings. This section will inform evolution of SoftDev.}
