from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Dialect
from sqlalchemy.sql import ClauseElement


def stringify_expression(expression: ClauseElement, dialect: Dialect = mysql.dialect()) -> str:
    """Complies, binds parameters and stringifies SQLAlchemy expression.

    Args:
        expression (ClauseElement): Source SQLAlchemy expression.
        dialect (Dialect): Specific sql dialect. Default mysql.

    Returns:
        str: Complied, bound and stringified expression.

    """
    expression_compiled = expression.compile(compile_kwargs={"literal_binds": True}, dialect=dialect)
    return str(expression_compiled)


def compile_expression(expression: ClauseElement, dialect: Dialect = mysql.dialect()) -> tuple[str, tuple[...]]:
    """Complies SQLAlchemy expression without binds parameters.

    Args:
        expression (ClauseElement): Source SQLAlchemy expression.
        dialect (Dialect): Specific sql dialect. Default mysql.

    Returns:
        tuple[str, tuple[...]]: Complied and stringified expression and tuple of parameters.

    """
    expression_compiled = expression.compile(dialect=dialect)
    return str(expression_compiled), tuple(expression_compiled.params.values())
