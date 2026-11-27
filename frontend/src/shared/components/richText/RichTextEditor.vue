<script setup lang="ts">
/**
 * The editor for recipe text: bold, italic, bullet and numbered lists, undo
 * and redo, with the usual shortcuts (Ctrl/Cmd+B, +I, +Shift+8, +Shift+7,
 * +Z, +Shift+Z). It reads and writes the Markdown subset of `markdown.ts`,
 * so the model is a plain string the backend stores as it is. Step text
 * also takes ingredient mentions (`mentionable`): typing `@` offers what
 * `mentions` finds, and the chips keep their Markdown token.
 */
import { onBeforeUnmount, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { EditorContent, useEditor } from '@tiptap/vue-3'

import { richTextExtensions, toEditorMarkdown } from '@/shared/components/richText/markdown'
import type { MentionSource } from '@/shared/components/richText/mentions'
import { suggestionPopup } from '@/shared/components/richText/suggestionPopup'

const model = defineModel<string>({ required: true })
const props = withDefaults(
  defineProps<{
    labelledby: string
    rows?: number
    invalid?: boolean
    inputId?: string
    mentionable?: boolean
    mentions?: MentionSource | null
  }>(),
  { rows: 3, invalid: false, inputId: undefined, mentionable: false, mentions: null },
)

const { t } = useI18n()

// The last Markdown this editor emitted, so an update that comes back
// through the model does not reset the cursor.
let emitted = model.value

const editor = useEditor({
  extensions: richTextExtensions(
    props.mentionable
      ? { mentions: props.mentions ? { ...props.mentions, render: suggestionPopup } : null }
      : {},
  ),
  content: toEditorMarkdown(model.value),
  contentType: 'markdown',
  editorProps: {
    attributes: {
      role: 'textbox',
      'aria-multiline': 'true',
      'aria-labelledby': props.labelledby,
      ...(props.inputId ? { id: props.inputId } : {}),
      class: 'rich-text-content',
    },
  },
  onUpdate: ({ editor: e }) => {
    // An emptied editor stores an empty string, not a lone line break.
    emitted = e.isEmpty ? '' : e.getMarkdown()
    model.value = emitted
  },
})

watch(model, (value) => {
  if (!editor.value || value === emitted) return
  emitted = value
  editor.value.commands.setContent(toEditorMarkdown(value), {
    contentType: 'markdown',
    emitUpdate: false,
  })
})

onBeforeUnmount(() => editor.value?.destroy())

const tools = [
  { key: 'bold', icon: 'mdi-format-bold', run: () => editor.value?.chain().focus().toggleBold().run() },
  { key: 'italic', icon: 'mdi-format-italic', run: () => editor.value?.chain().focus().toggleItalic().run() },
  {
    key: 'bulletList',
    icon: 'mdi-format-list-bulleted',
    run: () => editor.value?.chain().focus().toggleBulletList().run(),
  },
  {
    key: 'orderedList',
    icon: 'mdi-format-list-numbered',
    run: () => editor.value?.chain().focus().toggleOrderedList().run(),
  },
] as const
</script>

<template>
  <div
    class="rich-text-editor"
    :class="{ 'rich-text-editor--invalid': invalid }"
    :style="{ '--rich-text-rows': rows }"
  >
    <div class="rich-text-toolbar" role="toolbar" :aria-label="t('richText.toolbar')">
      <button
        v-for="tool in tools"
        :key="tool.key"
        type="button"
        class="rich-text-tool"
        :aria-pressed="editor?.isActive(tool.key) ?? false"
        :aria-label="t(`richText.${tool.key}`)"
        :title="t(`richText.${tool.key}`)"
        @click="tool.run()"
      >
        <span class="mdi" :class="tool.icon" aria-hidden="true" />
      </button>
      <span class="rich-text-separator" aria-hidden="true" />
      <button
        type="button"
        class="rich-text-tool"
        :disabled="!editor?.can().undo()"
        :aria-label="t('richText.undo')"
        :title="t('richText.undo')"
        @click="editor?.chain().focus().undo().run()"
      >
        <span class="mdi mdi-undo" aria-hidden="true" />
      </button>
      <button
        type="button"
        class="rich-text-tool"
        :disabled="!editor?.can().redo()"
        :aria-label="t('richText.redo')"
        :title="t('richText.redo')"
        @click="editor?.chain().focus().redo().run()"
      >
        <span class="mdi mdi-redo" aria-hidden="true" />
      </button>
    </div>
    <EditorContent :editor="editor" class="rich-text-body" />
  </div>
</template>

<style scoped lang="scss">
.rich-text-editor {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--p-inputtext-border-color);
  border-radius: var(--p-inputtext-border-radius);
  background: var(--p-inputtext-background);
  color: var(--p-inputtext-color);
  transition: border-color 0.15s ease;

  &:focus-within {
    border-color: var(--p-inputtext-focus-border-color);
    outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
    outline-offset: -1px;
  }
}

.rich-text-editor--invalid {
  border-color: var(--p-inputtext-invalid-border-color);
}

// The toolbar wraps on a narrow phone instead of scrolling, and every button
// is a full 44 px target.
.rich-text-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1);
  border-bottom: 1px solid var(--p-inputtext-border-color);
}

.rich-text-tool {
  display: grid;
  place-items: center;
  width: 2.75rem;
  height: 2.75rem;
  padding: 0;
  border: none;
  border-radius: var(--p-border-radius-sm);
  background: transparent;
  color: var(--p-text-muted-color);
  font-size: var(--font-size-xl);
  cursor: pointer;

  &:focus-visible {
    outline: var(--p-focus-ring-width) var(--p-focus-ring-style) var(--p-focus-ring-color);
  }

  &:disabled {
    cursor: default;
    opacity: 0.4;
  }

  &[aria-pressed='true'] {
    background: var(--p-highlight-background);
    color: var(--p-highlight-color);
  }
}

@media (hover: hover) {
  .rich-text-tool:not(:disabled):hover {
    background: var(--p-content-hover-background);
    color: var(--p-text-color);
  }
}

.rich-text-separator {
  width: 1px;
  height: 1.5rem;
  margin: 0 var(--space-1);
  background: var(--p-inputtext-border-color);
}

.rich-text-body :deep(.rich-text-content) {
  min-height: calc(var(--rich-text-rows) * 1.6em + 1rem);
  padding: var(--space-2) var(--space-3);
  outline: none;
  line-height: 1.6;
  overflow-wrap: anywhere;

  p {
    margin: 0 0 var(--space-2);
  }

  > :last-child {
    margin-bottom: 0;
  }

  ul,
  ol {
    margin: 0 0 var(--space-2);
    padding-left: var(--space-5);
  }

  .mention-chip {
    padding: 0 var(--space-1);
    border-radius: var(--p-border-radius-sm);
    background: var(--p-highlight-background);
    color: var(--p-highlight-color);
    font-weight: 700;
    white-space: nowrap;
  }

  .mention-chip[data-kind='recipe'] {
    text-decoration: underline dotted;
  }
}
</style>
