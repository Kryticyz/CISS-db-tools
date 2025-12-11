-- ============================================================================
-- Low Count Species Query with GBIF Image Counts
-- ============================================================================
--
-- This SQL script demonstrates the queries used to find species with low
-- image counts in the cleaned dataset and check GBIF availability.
--
-- Author: Tynan Matthews
-- E: tynan@matthews.solutions
--
-- Usage:
--   1. Connect to counts database
--   2. Attach GBIF database
--   3. Run the queries below
--
-- Example (SQLite command line):
--   sqlite3 plantnet_counts.db
--   sqlite> ATTACH DATABASE 'plantnet_gbif.db' AS gbif;
--   sqlite> .read src/low_count_species_query.sql
-- ============================================================================


-- ============================================================================
-- QUERY 1: Find species with checked count < 400
-- ============================================================================
--
-- This finds all species in the cleaned (checked) dataset with fewer than
-- 400 images. You can change the threshold (400) to any value you want.
-- You can also change 'checked_count' to 'unchecked_count' or 'original_count'
-- to query different datasets.
-- ============================================================================

SELECT
    directory AS species_name,
    checked_count AS local_count
FROM image_counts
WHERE checked_count IS NOT NULL
  AND checked_count < 400
ORDER BY checked_count DESC, directory ASC;


-- ============================================================================
-- QUERY 2: Get GBIF image count for a specific species
-- ============================================================================
--
-- Replace 'Acacia_dealbata' with any species name.
-- This counts how many images exist in GBIF for that species.
-- ============================================================================

-- First, attach the GBIF database (only needed once per session):
-- ATTACH DATABASE 'plantnet_gbif.db' AS gbif;

SELECT
    o.species_normalized AS species_name,
    COUNT(DISTINCT m.id) AS gbif_image_count
FROM gbif.multimedia m
INNER JOIN gbif.occurrences o ON m.gbifID = o.gbifID
WHERE o.species_normalized = 'Acacia_dealbata'
  AND m.type = 'StillImage'
GROUP BY o.species_normalized;


-- ============================================================================
-- QUERY 3: Combined query - Low count species with GBIF comparison
-- ============================================================================
--
-- This query combines both databases to show:
-- - Species with checked count < 400
-- - How many images they have in GBIF
-- - The difference between local and GBIF counts
--
-- IMPORTANT: You must attach the GBIF database first:
--   ATTACH DATABASE 'plantnet_gbif.db' AS gbif;
-- ============================================================================

ATTACH DATABASE 'plantnet_gbif.db' AS gbif;

SELECT
    c.directory AS species_name,
    c.checked_count AS local_count,
    COALESCE(gbif_counts.image_count, 0) AS gbif_images,
    COALESCE(gbif_counts.image_count, 0) - c.checked_count AS difference,
    CASE
        WHEN COALESCE(gbif_counts.image_count, 0) > 0 THEN 'Yes'
        ELSE 'No'
    END AS has_gbif_images
FROM image_counts c
LEFT JOIN (
    SELECT
        o.species_normalized,
        COUNT(DISTINCT m.id) AS image_count
    FROM gbif.multimedia m
    INNER JOIN gbif.occurrences o ON m.gbifID = o.gbifID
    WHERE m.type = 'StillImage'
    GROUP BY o.species_normalized
) AS gbif_counts ON c.directory = gbif_counts.species_normalized
WHERE c.checked_count IS NOT NULL
  AND c.checked_count < 400
ORDER BY c.checked_count DESC, c.directory ASC;


-- ============================================================================
-- QUERY 4: Top opportunities (most additional images in GBIF)
-- ============================================================================
--
-- This finds species where GBIF has significantly more images than the
-- local dataset, sorted by the number of additional images available.
-- ============================================================================

SELECT
    c.directory AS species_name,
    c.checked_count AS local_count,
    gbif_counts.image_count AS gbif_images,
    gbif_counts.image_count - c.checked_count AS additional_images
FROM image_counts c
INNER JOIN (
    SELECT
        o.species_normalized,
        COUNT(DISTINCT m.id) AS image_count
    FROM gbif.multimedia m
    INNER JOIN gbif.occurrences o ON m.gbifID = o.gbifID
    WHERE m.type = 'StillImage'
    GROUP BY o.species_normalized
) AS gbif_counts ON c.directory = gbif_counts.species_normalized
WHERE c.checked_count IS NOT NULL
  AND c.checked_count < 400
  AND gbif_counts.image_count > c.checked_count
ORDER BY (gbif_counts.image_count - c.checked_count) DESC
LIMIT 20;


-- ============================================================================
-- QUERY 5: Species with no GBIF images
-- ============================================================================
--
-- This identifies species in your local dataset (with count < 400) that
-- have zero images in GBIF. These may need alternative data sources.
-- ============================================================================

SELECT
    c.directory AS species_name,
    c.checked_count AS local_count,
    'No GBIF images' AS status
FROM image_counts c
LEFT JOIN (
    SELECT DISTINCT o.species_normalized
    FROM gbif.multimedia m
    INNER JOIN gbif.occurrences o ON m.gbifID = o.gbifID
    WHERE m.type = 'StillImage'
) AS gbif_species ON c.directory = gbif_species.species_normalized
WHERE c.checked_count IS NOT NULL
  AND c.checked_count < 400
  AND gbif_species.species_normalized IS NULL
ORDER BY c.checked_count DESC
LIMIT 20;


-- ============================================================================
-- QUERY 6: Summary statistics
-- ============================================================================
--
-- Provides overall statistics about low count species and GBIF coverage.
-- ============================================================================

WITH low_count_species AS (
    SELECT
        c.directory AS species_name,
        c.checked_count AS local_count,
        COALESCE(gbif_counts.image_count, 0) AS gbif_images
    FROM image_counts c
    LEFT JOIN (
        SELECT
            o.species_normalized,
            COUNT(DISTINCT m.id) AS image_count
        FROM gbif.multimedia m
        INNER JOIN gbif.occurrences o ON m.gbifID = o.gbifID
        WHERE m.type = 'StillImage'
        GROUP BY o.species_normalized
    ) AS gbif_counts ON c.directory = gbif_counts.species_normalized
    WHERE c.checked_count IS NOT NULL
      AND c.checked_count < 400
)
SELECT
    COUNT(*) AS total_species,
    SUM(local_count) AS total_local_images,
    SUM(gbif_images) AS total_gbif_images,
    SUM(gbif_images) - SUM(local_count) AS net_difference,
    SUM(CASE WHEN gbif_images > local_count THEN 1 ELSE 0 END) AS species_with_more_in_gbif,
    SUM(CASE WHEN gbif_images = local_count THEN 1 ELSE 0 END) AS species_with_same_count,
    SUM(CASE WHEN gbif_images < local_count THEN 1 ELSE 0 END) AS species_with_fewer_in_gbif,
    SUM(CASE WHEN gbif_images > 0 THEN 1 ELSE 0 END) AS species_with_gbif_images,
    SUM(CASE WHEN gbif_images = 0 THEN 1 ELSE 0 END) AS species_without_gbif_images
FROM low_count_species;


-- ============================================================================
-- QUERY 7: Different dataset comparisons
-- ============================================================================
--
-- Compare low count species across different cleaning stages:
-- - original_count: Before any cleaning
-- - checked_count: After manual checking
-- - unchecked_count: After automated cleaning
-- ============================================================================

-- Original dataset (< 400)
SELECT
    directory AS species_name,
    original_count AS count,
    'original' AS dataset
FROM image_counts
WHERE original_count IS NOT NULL
  AND original_count < 400
ORDER BY original_count DESC
LIMIT 10;

-- Checked dataset (< 400)
SELECT
    directory AS species_name,
    checked_count AS count,
    'checked' AS dataset
FROM image_counts
WHERE checked_count IS NOT NULL
  AND checked_count < 400
ORDER BY checked_count DESC
LIMIT 10;

-- Unchecked dataset (< 400)
SELECT
    directory AS species_name,
    unchecked_count AS count,
    'unchecked' AS dataset
FROM image_counts
WHERE unchecked_count IS NOT NULL
  AND unchecked_count < 400
ORDER BY unchecked_count DESC
LIMIT 10;


-- ============================================================================
-- NOTES
-- ============================================================================
--
-- 1. Species Naming:
--    - Both databases use normalized names in format: Genus_species
--    - Example: "Acacia dealbata Link" becomes "Acacia_dealbata"
--
-- 2. Image Types:
--    - We filter for m.type = 'StillImage' to exclude videos and other media
--
-- 3. Threshold:
--    - The threshold (400) can be changed to any value
--    - Lower values (e.g., 100) show very sparse species
--    - Higher values (e.g., 1000) show more broadly underrepresented species
--
-- 4. Performance:
--    - All queries use indexed columns for fast execution
--    - Typical execution time: < 1 second for most queries
--    - Query 3 (combined) may take 2-5 seconds with large datasets
--
-- 5. NULL Handling:
--    - COALESCE(value, 0) converts NULL to 0 for species not in GBIF
--    - IS NOT NULL ensures we only query species with valid counts
--
-- ============================================================================
