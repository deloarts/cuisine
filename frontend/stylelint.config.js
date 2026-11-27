/**
 * Stylelint for the global stylesheets and every component's <style> block.
 * The recommended sets catch mistakes (an unknown property, a duplicate
 * declaration, a selector that can never match) and leave formatting alone.
 */
export default {
  extends: ['stylelint-config-recommended-scss', 'stylelint-config-recommended-vue/scss'],
  plugins: ['stylelint-declaration-strict-value'],
  // Vendor stylesheets that ship with their fonts are kept as delivered.
  ignoreFiles: ['src/assets/fonts/**'],
  rules: {
    // A bare `//` line separates the paragraphs of a long comment.
    'scss/comment-no-empty': null,
    // The recommended set lets consecutive duplicates through as browser
    // fallbacks, which also let a second `transition` silently replace the
    // first. A fallback needs a disable comment that says why.
    'declaration-block-no-duplicate-properties': true,
    // Gaps, padding, margins and font sizes come from the tokens in
    // main.scss. Sizes relative to the element (em) or the screen (vmin,
    // clamp, calc) stay literal. Padding and margins also keep auto, a 1px hairline and negative
    // values, which pull an element over its container's padding rather than
    // space it out.
    'scale-unlimited/declaration-strict-value': [
      ['/^(row-|column-)?gap$/', '/^(padding|margin)/', 'font-size', '/color$/', 'background', 'fill', 'stroke'],
      {
        ignoreValues: [
          '0',
          'auto',
          '1px',
          'inherit',
          'none',
          'transparent',
          'currentColor',
          '/^-/',
          '/^-?[0-9.]+(em|vmin|vh|vw|%)$/',
          '/^(calc|clamp|min|max)\\(/',
        ],
        disableFix: true,
      },
    ],
    // Colour literals belong in a token definition (a custom property), either
    // in main.scss or, for a screen with its own fixed palette, on that
    // screen's root element. This also reaches into the shorthands the rule
    // above cannot see into, such as border, box-shadow and gradients, and
    // catches rgba() and hsla(), which that rule lets through as functions.
    'declaration-property-value-disallowed-list': {
      '/^(?!--)/': ['/\\b(rgba?|hsla?)\\(/', '/#[0-9a-fA-F]{3,8}\\b/'],
    },
    // Media queries take a breakpoint from assets/styles/_breakpoints.scss.
    'scss/media-feature-value-dollar-variable': ['always', { ignore: ['keywords'] }],
    // Vue's scoped-style escapes.
    'selector-pseudo-class-no-unknown': [true, { ignorePseudoClasses: ['deep', 'global', 'slotted'] }],
    'selector-pseudo-element-no-unknown': [true, { ignorePseudoElements: ['v-deep', 'v-global', 'v-slotted'] }],
  },
  overrides: [
    {
      // OpenVue's internal .p-* class names are not a public interface, so a
      // component never styles them. It puts one of the named classes from
      // assets/styles/_openvue.scss on the OpenVue component, sets one of the
      // theme's --p-* variables, or adds its own class through the class
      // attribute or pass-through (pt). .p-dark is the theme switch, not an
      // internal element, and stays allowed.
      files: ['**/*.vue'],
      rules: {
        'selector-disallowed-list': [
          ['/\\.p-(?!dark\\b)[a-z]/'],
          {
            splitList: true,
            message: 'Style OpenVue through _openvue.scss, a --p-* variable or a class of your own, not its .p-* classes',
          },
        ],
      },
    },
  ],
}
