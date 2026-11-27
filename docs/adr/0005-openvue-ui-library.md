# 0005 OpenVue as the UI component library

- Status: accepted
- Date: 2026-11-21

## context

The frontend needs tables, dialogs, forms, menus, toasts and a theme that switches between light and dark and between accent colours per user. Glados already solved this with OpenVue and a set of tokens, shared classes and style rules, and its look is what the users of both apps know.

## decision

Cuisine uses OpenVue 1 with its themes package, auto-imported per component, and the Glados styling rules: tokens in `themePresets.ts`, shared classes in `main.scss` and `_openvue.scss`, spacing and colour tokens enforced by stylelint, no styling of OpenVue's internal classes in components, and no utility-CSS framework. The default theme is the monochrome `soul` palette (black accent on a light surface) instead of the Glados blue, and the type is Nunito with Lobster for the wordmark and page titles, both self-hosted.

## consequences

Pages are built from ready components and look like Glados without extra design work, and improvements to the shared styles carry over between the two projects by hand. The four theme presets ship in the entry chunk, which makes it larger than Vite's default warning limit.
