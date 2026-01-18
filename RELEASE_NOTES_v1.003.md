v1.003 - Variant-first catalog change

- Added `is_catalog_only` flag to `items` to support catalog-only parent items. Items with variants are migrated to `is_catalog_only = 1`.
- POS now shows variant entries directly for catalog-only parents (e.g., "Coffee — Small"). Selecting a variant adds the specific variant to the cart and tracks stock at variant level.
- Inventory view will display variants as top-level rows for catalog-only parents to simplify stock management.
- Migration: on startup the database will add the `is_catalog_only` column and mark existing items that have variants as catalog-only. This is idempotent and safe for existing installations.
- Tests added to verify variant behavior and UI changes.

Notes:
- Parent items remain useful for grouping; they are no longer sellable directly when catalog-only is enabled.
- If you prefer to keep parent items sellable, set `is_catalog_only` to 0 for that item and the UI will keep the previous parent + child variant layout.
