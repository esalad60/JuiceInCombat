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
Ivan Chen | ivanc178@nycstudents.net | Backend Developer | Front-end Developer
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
1. Elo

## Explicit Non-Goals

Features intentionally excluded:
- More than one player on each team in combat
- AI-controlled armies
- A campaign of sorts
- Sidegrades of extra units

---

# Technology Stack

| Layer | Selected Tool |
|---|---|
| Backend Framework | Flask |
| Frontend Framework | tailwind |
| Database | SQLite |
| Authentication | username/password |
| ORM / DB Library | optionally SQLAlchemy; initiate clearance protocol if interested |
| Server | FlaskSocketIO

## Why This Stack Was Chosen
We prefer to work with technology that we know the best, primarily since a lot of what we're planning on doing requires learning/implementing other software that not all of us are familiar with. By using Flask, tailwing, SQLite we can limit the amount of variables that few of us know and thus can work together more fluidly.

---

# Team Ownership Plan

Each member must own meaningful deliverables.

| Team Member | Primary Ownership | Secondary Ownership | Specific Deliverables |
|---|---|---|---|
|Ethan|Backend Game Logic|Frontend Animation|Working serverside registering of units in battle using rudimentary array displays|
|Eviss|Working Server|Working Server calls|Server-Player and Peer to Peer communication|
|Lucas|Game Rendering|Gameplay|Render the game, units, and make the gamplay happen|
| | | | |

---

# Component map

<img width="3522" height="1380" alt="mermaid-diagram (2)" src="https://github.com/user-attachments/assets/fd0052fd-5e4a-437c-ad11-64fd851109e2" />



# Site map

<img width="2108" height="1113" alt="mermaid-diagram (1)" src="https://github.com/user-attachments/assets/bd170e42-fe14-4f5d-8bb3-4030057ed86f" />


## Key User Stories
### eg0
As a gamer, I want to game so that I can gain dopamine

### eg1
As a skibidi toilet fan, I want to have fun so that I will be able to wait for the episode 80 of skibid toilet to come out

### eg2
As a __________, I want to __________ so that...



# Database Design

{Insert your table/document organizational structure here}


# Testing Plan
{Delineate here your plan for testing each component}

# Timeline
Week 1 Goals: May 17
Finalize unit types, building types, and basic game rules
Create Flask project structure
Set up SQLite database
Build basic room creation and joining system
Create a simple test map using arrays
Week 2 Goals: May 24
All on backend:
  Implement unit movement
  Implement combat system
  Implement basic economy and building income
Start frontend game board rendering
Connect frontend buttons to backend routes
Week 3 Goals: May 25–May 31
Add at least five working unit types
Add at least two armies
Add basic research tree/tutorial (?)
Improve 3D map rendering and UI
Test full match from start to finish
Final Patches: June 5
Fix bugs
Balance unit stats
Clean up UI
Finish documentation
Prepare final presentation/demo

# Completion Criteria (_a.k.a._ "Definition of 'Done'")
Project is considered complete when all of the following are true:
1. Two players can create or join a room and start a match.
2. The game displays a working 3D map.
3. Players can move units, attack enemies, and end their turns.
4. Buildings generate income and allow players to create units.
5. At least five different units are implemented.
6. A basic research tree unlocks units or upgrades.
7. A player can win by capturing the enemy capital.


# Open Questions
1. Balancing? Should we have a research tree in general or unlock different equal value army templates?
2. How much of the game should be stored locally? [i.e, does the client recieve the entire map or just what their units can see]
3. Terrain generation... maps in general, how?

# Appendix
Basic 5 units include the following
1. Standard infantry
2. Standard artillery
3. Anti-armor infantry
4. Armored unit
5. Supply unit
Terrain will provide some kind of stats, defense, sight etc,
We will use a lot of OOP and python classes

# Other

