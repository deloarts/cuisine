/**
 * The download name of a recipe's `.cui` file, the same slug the backend
 * puts into its Content-Disposition header: lower case ASCII letters, digits
 * and hyphens, at most 80 characters, or `recipe.cui` when nothing is left.
 */
export function cuiFileName(title: string): string {
  const ascii = title.normalize('NFKD').replace(/[\u0080-\uffff]/g, '')
  const slug = ascii
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80)
    .replace(/-+$/, '')
  return `${slug || 'recipe'}.cui`
}
