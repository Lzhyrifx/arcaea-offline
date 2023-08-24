from typing import Optional

from sqlalchemy import TEXT, case, func, inspect, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy_utils import create_view

from .songs import Chart, ChartInfo

__all__ = [
    "ScoresBase",
    "Score",
    "Calculated",
    "Best",
    "CalculatedPotential",
]


class ScoresBase(DeclarativeBase):
    pass


class Score(ScoresBase):
    __tablename__ = "score"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    song_id: Mapped[str] = mapped_column(TEXT())
    rating_class: Mapped[int]
    score: Mapped[int]
    pure: Mapped[Optional[int]]
    far: Mapped[Optional[int]]
    lost: Mapped[Optional[int]]
    date: Mapped[Optional[int]]
    max_recall: Mapped[Optional[int]]
    r10_clear_type: Mapped[Optional[int]] = mapped_column(
        comment="0: LOST, 1: COMPLETE, 2: HARD_LOST"
    )


# How to create an SQL View with SQLAlchemy?
# https://stackoverflow.com/a/53253105/16484891
# CC BY-SA 4.0


class Calculated(ScoresBase):
    score_id: Mapped[str]
    song_id: Mapped[str]
    rating_class: Mapped[int]
    score: Mapped[int]
    pure: Mapped[Optional[int]]
    far: Mapped[Optional[int]]
    lost: Mapped[Optional[int]]
    date: Mapped[Optional[int]]
    max_recall: Mapped[Optional[int]]
    r10_clear_type: Mapped[Optional[int]]
    shiny_pure: Mapped[Optional[int]]
    potential: Mapped[float]

    __table__ = create_view(
        name="calculated",
        selectable=select(
            Score.id.label("score_id"),
            Chart.song_id,
            Chart.rating_class,
            Score.score,
            Score.pure,
            Score.far,
            Score.lost,
            Score.date,
            Score.max_recall,
            Score.r10_clear_type,
            (
                Score.score
                - func.floor(
                    (Score.pure * 10000000.0 / ChartInfo.note)
                    + (Score.far * 0.5 * 10000000.0 / ChartInfo.note)
                )
            ).label("shiny_pure"),
            case(
                (Score.score >= 10000000, ChartInfo.constant / 10.0 + 2),
                (
                    Score.score >= 9800000,
                    ChartInfo.constant / 10.0 + 1 + (Score.score - 9800000) / 200000.0,
                ),
                else_=func.max(
                    (ChartInfo.constant / 10.0) + (Score.score - 9500000) / 300000.0,
                    0,
                ),
            ).label("potential"),
        )
        .select_from(Chart)
        .join(
            ChartInfo,
            (Chart.song_id == ChartInfo.song_id)
            & (Chart.rating_class == ChartInfo.rating_class),
        )
        .join(
            Score,
            (Chart.song_id == Score.song_id)
            & (Chart.rating_class == Score.rating_class),
        ),
        metadata=ScoresBase.metadata,
    )


class Best(ScoresBase):
    score_id: Mapped[str]
    song_id: Mapped[str]
    rating_class: Mapped[int]
    score: Mapped[int]
    pure: Mapped[Optional[int]]
    far: Mapped[Optional[int]]
    lost: Mapped[Optional[int]]
    date: Mapped[Optional[int]]
    max_recall: Mapped[Optional[int]]
    r10_clear_type: Mapped[Optional[int]]
    shiny_pure: Mapped[Optional[int]]
    potential: Mapped[float]

    __table__ = create_view(
        name="best",
        selectable=select(
            *[col for col in inspect(Calculated).columns if col.name != "potential"],
            func.max(Calculated.potential).label("potential"),
        )
        .select_from(Calculated)
        .group_by(Calculated.song_id, Calculated.rating_class)
        .order_by(Calculated.potential.desc()),
        metadata=ScoresBase.metadata,
    )


class CalculatedPotential(ScoresBase):
    b30: Mapped[float]

    _select_bests_subquery = (
        select(Best.potential.label("b30_sum"))
        .order_by(Best.potential.desc())
        .limit(30)
        .subquery()
    )
    __table__ = create_view(
        name="calculated_potential",
        selectable=select(func.avg(_select_bests_subquery.c.b30_sum).label("b30")),
        metadata=ScoresBase.metadata,
    )
