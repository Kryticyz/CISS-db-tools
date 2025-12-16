# Manual UI Testing Checklist

This document provides a comprehensive checklist for manually testing the UI functionality of the duplicate image review application.

## Prerequisites

- [ ] Server is running (`python review_duplicates_v2.py <path_to_images>`)
- [ ] Browser is open to `http://localhost:8000`
- [ ] Test dataset has at least 2-3 species with duplicate/similar images

## Test Session Information

- **Date**: _______________
- **Tester**: _______________
- **Browser**: _______________
- **Dataset**: _______________

---

## 1. Mode Selection Screen

### Visual Appearance
- [ ] Page loads without errors
- [ ] Header "🌿 Plant Image Duplicate Finder" is visible
- [ ] Three mode cards are displayed (Duplicates, Similar, Outliers)
- [ ] Icons are visible on each card (🔍, 🎨, ⚠️)
- [ ] Card descriptions are clear and readable
- [ ] Scope selector section is visible

### Interactivity
- [ ] Clicking on a mode card highlights it (border changes color)
- [ ] Only one mode can be selected at a time
- [ ] "All Species" radio button is selected by default
- [ ] Species dropdown is hidden when "All Species" is selected
- [ ] Switching to "Single Species" shows the dropdown
- [ ] Species dropdown is disabled when "All Species" is selected
- [ ] Species dropdown is enabled when "Single Species" is selected
- [ ] Species dropdown contains list of available species
- [ ] Species names are formatted correctly (spaces instead of underscores)

### Hover Effects
- [ ] Mode cards lift up on hover (translateY effect)
- [ ] Mode cards show shadow on hover
- [ ] Cursor changes to pointer on hoverable elements

### Button Functionality
- [ ] "Start Analysis" button is enabled
- [ ] Clicking "Start Analysis" without selecting mode shows alert
- [ ] Clicking "Start Analysis" with "Single Species" but no species shows alert
- [ ] Clicking "Start Analysis" with valid selection proceeds to results

---

## 2. Results Display

### Initial Loading
- [ ] Loading spinner appears when analysis starts
- [ ] Loading message is displayed
- [ ] No console errors during loading

### Results Header
- [ ] Results header shows correct count (e.g., "Found X groups across Y species")
- [ ] Stats show total images scanned
- [ ] "Back to Mode Selection" button is visible and works

### All Species Mode
- [ ] Results are grouped by species
- [ ] Each species section shows species name (formatted correctly)
- [ ] Each species section shows count of groups found
- [ ] Multiple species are displayed if results exist

### Single Species Mode
- [ ] Results show only the selected species
- [ ] Groups are displayed correctly

### Empty Results
- [ ] When no duplicates/similar images found, shows appropriate message
- [ ] Message is user-friendly (not technical error)

---

## 3. Image Groups

### Group Display
- [ ] Groups are displayed with clear headers
- [ ] Group header shows "Group X: Y images"
- [ ] Groups are collapsed by default
- [ ] Clicking group header expands/collapses content
- [ ] Arrow indicator (▼) is visible in header

### Group Actions
- [ ] "Select All But Largest" button is visible on each group
- [ ] Button click doesn't collapse the group
- [ ] Button correctly selects all images except the largest

### Expanded Group Content
- [ ] Images are displayed in a grid layout
- [ ] Grid is responsive (adjusts to screen size)
- [ ] Images maintain aspect ratio
- [ ] Lazy loading works (images load as you scroll)

---

## 4. Image Selection

### Visual Indicators
- [ ] Each image has a checkbox in the top-right corner
- [ ] Checkbox is initially empty (not selected)
- [ ] Clicking an image toggles selection
- [ ] Selected images show checkmark (✓) in checkbox
- [ ] Selected images have red border
- [ ] Selected images have red shadow/glow effect
- [ ] Largest image in group has green border (marked as "keep")

### Image Information
- [ ] Filename is displayed below each image
- [ ] Long filenames are truncated with ellipsis
- [ ] File size is displayed in KB
- [ ] Largest image shows "🟢 Largest" badge
- [ ] Smaller images show "🟡 Smaller" badge

### Image Preview
- [ ] Clicking on image thumbnail opens full-size preview
- [ ] Preview modal has dark background
- [ ] Full-size image is centered
- [ ] Close button (×) is visible in top-right
- [ ] Clicking background closes preview
- [ ] Pressing Escape key closes preview
- [ ] Preview doesn't toggle selection (selection requires clicking the card itself)

### Selection Counter
- [ ] Footer shows "X images selected for deletion"
- [ ] Counter updates immediately when images are selected/deselected
- [ ] Counter shows 0 when nothing is selected

---

## 5. Quick Selection Features

### "Select All But Largest" Button
- [ ] Button appears on each group
- [ ] Clicking selects all images except the one marked as largest
- [ ] Previously selected images remain selected
- [ ] Visual feedback is immediate
- [ ] Selection counter updates correctly

### For Duplicate Mode
- [ ] "Select Duplicates" button appears (if applicable)
- [ ] Clicking selects all duplicate images (not the kept one)
- [ ] Kept image (green border) is not selected

---

## 6. Sticky Footer

### Visibility
- [ ] Footer is visible at bottom of screen
- [ ] Footer stays visible when scrolling (sticky)
- [ ] Footer shows selection count
- [ ] Footer shows action buttons

### Button States
- [ ] "Clear Selection" button is always enabled
- [ ] "Delete Selected" button is disabled when count is 0
- [ ] "Delete Selected" button is enabled when count > 0
- [ ] Button labels are clear

### Actions
- [ ] "Clear Selection" button deselects all images
- [ ] Visual indicators (checkmarks, borders) are removed
- [ ] Counter resets to 0
- [ ] "Delete Selected" button opens confirmation modal

---

## 7. Deletion Confirmation Modal

### Modal Appearance
- [ ] Modal appears when "Delete Selected" is clicked
- [ ] Modal has semi-transparent dark background
- [ ] Modal content is centered
- [ ] Warning icon (⚠️) is visible

### Information Display
- [ ] Shows correct count of images to delete
- [ ] Shows count of species affected
- [ ] Shows total size to be freed (in MB)
- [ ] Warning message "This cannot be undone!" is prominent

### File List
- [ ] "View list of files to delete" is collapsed by default
- [ ] Clicking expands to show file list
- [ ] File paths are displayed correctly
- [ ] List is scrollable if many files

### Modal Actions
- [ ] "Cancel" button closes modal without deleting
- [ ] "Yes, Delete Files" button proceeds with deletion
- [ ] Clicking outside modal does NOT close it (safety)
- [ ] Pressing Escape closes modal (cancelled)

---

## 8. Deletion Progress

### Progress Modal
- [ ] Progress modal appears after confirming deletion
- [ ] Modal shows "Deleting Files..." title
- [ ] Progress bar is visible
- [ ] Progress bar starts at 0%

### Progress Updates
- [ ] Progress bar fills as deletion proceeds
- [ ] Percentage is displayed on progress bar
- [ ] Text below shows "X of Y files"
- [ ] Progress updates are smooth

### Cannot Cancel
- [ ] Modal cannot be closed during deletion
- [ ] No close button is available
- [ ] Clicking outside doesn't close modal

---

## 9. Deletion Completion

### Success Message
- [ ] Modal closes after completion
- [ ] Success message appears in results view
- [ ] Message shows "✅ Deletion Complete"
- [ ] Shows count of successfully deleted files
- [ ] Shows count of failed deletions (if any)

### Results Refresh
- [ ] Deleted images are removed from the display
- [ ] Groups with all images deleted are removed
- [ ] If no images remain, shows "No duplicates found" message
- [ ] Selection is cleared (counter shows 0)

### Error Handling
- [ ] If deletion fails, error message is shown
- [ ] Error message is user-friendly
- [ ] Can proceed to try again or go back

---

## 10. Navigation Flow

### Back Navigation
- [ ] "Back to Mode Selection" button works from results view
- [ ] Returns to mode selection screen
- [ ] Mode selection is reset (no mode selected)
- [ ] Scope returns to "All Species"
- [ ] Can start a new analysis

### Multiple Analyses
- [ ] Can run analysis multiple times
- [ ] Previous results are cleared
- [ ] No memory leaks or performance degradation
- [ ] Selection state is reset between analyses

---

## 11. Responsive Design

### Desktop (> 1200px)
- [ ] Layout uses full width appropriately
- [ ] Image grid shows 3-4 columns
- [ ] All elements are properly sized
- [ ] No horizontal scrolling needed

### Tablet (768px - 1200px)
- [ ] Layout adapts to smaller width
- [ ] Image grid shows 2-3 columns
- [ ] Touch targets are appropriate size
- [ ] Footer remains functional

### Mobile (< 768px)
- [ ] Mode cards stack vertically
- [ ] Image grid shows 2 columns
- [ ] Footer stacks buttons vertically
- [ ] Text is readable without zooming
- [ ] Touch targets are at least 44x44px

---

## 12. Error Handling

### Network Errors
- [ ] If API fails, shows error message
- [ ] Error message is user-friendly (not technical)
- [ ] Can retry the operation
- [ ] Console shows details for debugging

### Invalid Data
- [ ] Handles missing species gracefully
- [ ] Handles empty results gracefully
- [ ] Handles malformed API responses

### Browser Compatibility
- [ ] Works in Chrome/Edge
- [ ] Works in Firefox
- [ ] Works in Safari
- [ ] No console errors in any browser

---

## 13. Performance

### Load Time
- [ ] Initial page loads in < 2 seconds
- [ ] Species list loads quickly
- [ ] Analysis completes in reasonable time

### Image Loading
- [ ] Images load progressively (lazy loading)
- [ ] No layout shift when images load
- [ ] Thumbnails are appropriately sized

### Smooth Interactions
- [ ] No lag when clicking/selecting
- [ ] Animations are smooth (60fps)
- [ ] No freezing during deletion
- [ ] Large datasets (100+ images) remain responsive

---

## 14. Accessibility

### Keyboard Navigation
- [ ] Can tab through interactive elements
- [ ] Tab order is logical
- [ ] Focused elements have visible outline
- [ ] Can activate buttons with Enter/Space
- [ ] Can close modals with Escape

### Screen Reader (Optional)
- [ ] Images have alt text
- [ ] Buttons have descriptive labels
- [ ] Form fields have labels
- [ ] Status messages are announced

---

## 15. Edge Cases

### Large Datasets
- [ ] Handles 500+ images without crashing
- [ ] Handles 50+ species
- [ ] Handles 100+ groups
- [ ] Performance remains acceptable

### Special Characters
- [ ] Handles filenames with spaces
- [ ] Handles filenames with special chars ((), -, _)
- [ ] Handles non-ASCII characters in species names

### Empty States
- [ ] Handles empty species folder
- [ ] Handles species with only 1 image
- [ ] Handles dataset with no duplicates

---

## Notes and Issues Found

| Issue # | Description | Severity | Status |
|---------|-------------|----------|--------|
| 1       |             |          |        |
| 2       |             |          |        |
| 3       |             |          |        |

**Severity Levels**: 
- Critical: Blocks main functionality
- High: Major feature broken
- Medium: Minor feature issue
- Low: Cosmetic issue

---

## Test Summary

**Total Tests**: _____ / _____  
**Passed**: _____  
**Failed**: _____  
**Pass Rate**: _____%

**Overall Assessment**: 
- [ ] Ready for production
- [ ] Needs minor fixes
- [ ] Needs major fixes
- [ ] Not ready

**Tester Signature**: _______________
**Date**: _______________
