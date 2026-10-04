from sqlmodel import Session, SQLModel, select

from app.database import engine
from app.models import Hero, Mission, Team


def seed():
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        existing_team = session.exec(select(Team)).first()

        if existing_team:
            print("Database already seeded.")
            return

        # =========================
        # TEAMS
        # =========================
        avengers = Team(
            name="Avengers",
            headquarters="New York"
        )

        xmen = Team(
            name="X-Men",
            headquarters="Westchester"
        )

        # =========================
        # MISSIONS
        # =========================
        sokovia = Mission(
            title="Battle of Sokovia"
        )

        rescue = Mission(
            title="Rescue Mission"
        )

        # =========================
        # HEROES
        # =========================
        tony = Hero(
            name="Tony",
            age=45,
            secret_name="Iron Man",
            team=avengers,
            missions=[sokovia]
        )

        natasha = Hero(
            name="Natasha",
            age=35,
            secret_name="Black Widow",
            team=avengers,
            missions=[sokovia, rescue]
        )

        steve = Hero(
            name="Steve",
            age=100,
            secret_name="Captain America",
            team=avengers,
            missions=[rescue]
        )

        logan = Hero(
            name="Logan",
            age=150,
            secret_name="Wolverine",
            team=xmen,
            missions=[rescue]
        )

        scott = Hero(
            name="Scott",
            age=30,
            secret_name="Cyclops",
            team=xmen
        )

        session.add(avengers)
        session.add(xmen)
        session.add(sokovia)
        session.add(rescue)

        session.add(tony)
        session.add(natasha)
        session.add(steve)
        session.add(logan)
        session.add(scott)

        session.commit()

        print("Database seeded successfully.")


if __name__ == "__main__":
    seed()