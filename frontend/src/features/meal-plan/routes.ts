import type { RouteRecordRaw } from 'vue-router'

export default [
  {
    path: '/meal-plan',
    name: 'meal-plan',
    component: () => import('@/features/meal-plan/views/MealPlanView.vue'),
    meta: { title: 'nav.mealPlan' },
  },
] satisfies RouteRecordRaw[]
