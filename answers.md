# Week 9 Lab – Answers

## Question 1

**For each of the four statements, which constraint blocked it (`PRIMARY KEY`, `UNIQUE`, `NOT NULL`, `FOREIGN KEY`) and why?**

### 1. Duplicate team name

```sql
INSERT INTO team (name, headquarters)
VALUES ('Avengers', 'Los Angeles');
```

**Answer:**  
This statement is blocked by the `UNIQUE` constraint because the `team.name` column is defined as unique. A team named `Avengers` already exists, so PostgreSQL does not allow another row with the same name.


### 2. Hero with a non-existing team

```sql
INSERT INTO hero (name, team_id)
VALUES ('Ghost', 99);
```

**Answer:**  
This statement is blocked by the `FOREIGN KEY` constraint. The `team_id` column references `team(id)`, but there is no team with `id = 99`.


### 3. Hero without a name

```sql
INSERT INTO hero (age)
VALUES (30);
```

**Answer:**  
This statement is blocked by the `NOT NULL` constraint because the `name` column of the `hero` table is required and cannot be `NULL`.


### 4. Delete a team that is still referenced by heroes

```sql
DELETE FROM team
WHERE id = 1;
```

**Answer:**  
This statement is blocked by the `FOREIGN KEY` constraint because some rows in the `hero` table still reference `team.id = 1`. PostgreSQL prevents deleting the referenced team to preserve referential integrity.


## Question 2

**The relationship `team → hero` is one-to-many. Why is the foreign key on `hero` and not on `team`?**

**Answer:**  
The foreign key is stored in the `hero` table because each hero belongs to zero or one team, while one team can have many heroes.

Therefore, each hero row only needs one `team_id` value to identify its team.

If the foreign key were stored in the `team` table, one team would need to store multiple hero IDs, which does not fit the relational database structure well.

So the relationship is represented as:

```text
Team
  1
  |
  |
  *
Hero
```

and the foreign key is:

```text
hero.team_id → team.id
```


## Question 3

**Heroes can go on many missions and a mission has many heroes (many-to-many). Sketch the tables you need (names, columns, PK, FK). Hint: you need a link table.**

**Answer:**  
A many-to-many relationship requires three tables:

```text
Hero
----------------
id          PK
name
age
team_id     FK → Team.id


Mission
----------------
id          PK
title


HeroMissionLink
----------------
hero_id     PK, FK → Hero.id
mission_id  PK, FK → Mission.id
```

`HeroMissionLink` is the link table between `Hero` and `Mission`.

The pair:

```text
(hero_id, mission_id)
```

forms a composite primary key.

This allows:

- one hero to participate in many missions;
- one mission to contain many heroes.

For example:

```text
HeroMissionLink

hero_id | mission_id
--------|-----------
1       | 1
1       | 2
2       | 1
```

This means Hero 1 participates in Missions 1 and 2, while Mission 1 contains Heroes 1 and 2.


## Question 4

**Why read the URL from an environment variable instead of writing it in `database.py`? Give two reasons.**

**Answer:**

### 1. Security

The database URL can contain sensitive information such as:

```text
username
password
host
database name
```

If the URL is hardcoded directly in `database.py`, it may accidentally be committed and pushed to GitHub.

Using an environment variable keeps database credentials outside the source code.

For example:

```bash
export DATABASE_URL="postgresql+psycopg://app:secret@localhost:5432/appdb"
```

### 2. Easier configuration for different environments

Different environments can use different databases without changing the Python source code.

For example:

```text
Development → local PostgreSQL
Testing     → test database
Production  → production PostgreSQL server
```

The application can use the same code while only changing the `DATABASE_URL` environment variable.