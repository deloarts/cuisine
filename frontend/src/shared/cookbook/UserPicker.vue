<script setup lang="ts">
/**
 * Picks people of this instance by name, each shown with their avatar in the
 * list and in the chosen chips. Without `people` it offers the directory every
 * signed-in user may read and leaves out the signed-in user; a caller that
 * narrows the choice (a recipe's possible co-editors, a group's members)
 * passes its own list, offered as given.
 */
import { computed, onMounted, ref } from 'vue'

import { useCurrentUserStore } from '@/core/stores/currentUserStore'
import { listDirectory } from '@/shared/api/directory'
import PersonOption from '@/shared/components/PersonOption.vue'

/** What the picker needs of a person. */
interface PickablePerson {
  id: string
  display_name: string
  avatar_id?: string | null
}

const props = withDefaults(
  defineProps<{ inputId: string; labelledby: string; disabled?: boolean; people?: readonly PickablePerson[] | null }>(),
  { disabled: false, people: null },
)
const model = defineModel<string[]>({ default: () => [] })

const currentUser = useCurrentUserStore()
const directory = ref<PickablePerson[]>([])
const options = computed(() =>
  props.people ? [...props.people] : directory.value.filter((p) => p.id !== currentUser.user?.id),
)
const byId = computed(() => new Map(options.value.map((p) => [p.id, p])))

onMounted(async () => {
  if (props.people) return
  try {
    directory.value = await listDirectory()
  } catch {
    directory.value = []
  }
})
</script>

<template>
  <MultiSelect
    v-model="model"
    :input-id="props.inputId"
    :options="options"
    option-label="display_name"
    option-value="id"
    :aria-labelledby="props.labelledby"
    :disabled="props.disabled"
    display="chip"
    filter
    fluid
  >
    <template #option="{ option }">
      <PersonOption :name="option.display_name" :avatar-id="option.avatar_id" />
    </template>
    <template #chip="{ value, removeCallback }">
      <Chip :removable="!props.disabled" @remove="removeCallback($event, value)">
        <PersonOption
          :name="byId.get(value)?.display_name ?? ''"
          :avatar-id="byId.get(value)?.avatar_id"
          size="small"
        />
      </Chip>
    </template>
  </MultiSelect>
</template>
