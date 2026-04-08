from .meal_confirm import router as meal_confirm_router
from .templates import router as templates_router
from .activity import router as activity_router
from .start import router as start_router
from .food import router as food_router
from .stats import router as stats_router


# Порядок ВАЖЕН:
# 1. stateful роутеры идут раньше, чтобы FSM-хендлеры имели приоритет.
# 2. свободный food router идёт после них и работает только в neutral state.
all_routers = [meal_confirm_router, templates_router, activity_router, start_router, food_router, stats_router]
