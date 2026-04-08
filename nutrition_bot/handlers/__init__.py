from .meal_confirm import router as meal_confirm_router
from .templates import router as templates_router
from .activity import router as activity_router
from .food import router as food_router
from .start import router as start_router
from .stats import router as stats_router


# Порядок ВАЖЕН: meal_confirm должен быть ПЕРВЫМ чтобы перехватывать
# текстовые сообщения во время редактирования (FSM state filter).
all_routers = [meal_confirm_router, templates_router, activity_router, food_router, start_router, stats_router]
