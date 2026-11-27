/**
 * Wire types of the cookbook API that several features share, aliased from
 * the generated schema so a backend change fails the type-check.
 */
import type { Schemas } from '@/core/api/generated'

export type Allergen = Schemas['Allergen']
export type ContentLocale = Schemas['ContentLocale']
export type UnitKind = Schemas['UnitKind']
export type TagKind = Schemas['TagKind']
export type MealSlot = Schemas['MealSlot']
export type RestrictionKind = Schemas['RestrictionKind']
export type IngredientStatus = Schemas['IngredientStatus']
export type EquipmentKind = Schemas['EquipmentKind']

export type UnitResponse = Schemas['UnitResponse']
export type TagResponse = Schemas['TagResponse']
export type CategoryResponse = Schemas['CategoryResponse']
export type FamilyResponse = Schemas['FamilyResponse']
export type IngredientListItem = Schemas['IngredientListItem']
// The backend's IngredientResponse, which the API only serves as a list item
// or a detail, so the snapshot holds no schema of its own for it.
export type IngredientResponse = Omit<IngredientListItem, 'usage_count'>
export type RecipeSummaryResponse = Schemas['RecipeSummaryResponse']
export type UserSummaryResponse = Schemas['UserSummaryResponse']
export type DirectoryUserResponse = Schemas['DirectoryUserResponse']
export type PersonRef = Schemas['PersonRef']
export type RecipeRef = Schemas['RecipeRef']
export type UnitRef = Schemas['UnitRef']
export type EquipmentResponse = Schemas['EquipmentResponse']
export type EquipmentRef = Schemas['EquipmentRef']

/** The details an ingredient suggestion row can show (`IngredientOption.vue`). */
export type IngredientMeta = 'category' | 'family' | 'allergens' | 'draft' | 'season' | 'owner' | 'locale'
