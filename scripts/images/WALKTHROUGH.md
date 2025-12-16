# 🌿 Complete Walkthrough: Batch Embeddings → Review UI

## Overview

This guide walks you through the complete workflow from generating CNN embeddings to reviewing and deleting duplicate images using the modern web interface.

---

## 📊 Your Current Setup

**Dataset Location**: `/Users/kryticyz/Documents/life/CISS/plantNet/data/images/by_species`

**Embeddings Status**: ✅ Already generated!
- **Location**: `data/databases/embeddings/plantnet_drive/`
- **Total images**: 141,691
- **Total species**: 746
- **Model**: ResNet18
- **Index size**: 141,691 vectors
- **Dimension**: 512
- **Errors**: 0

**Current species in your dataset** (showing first few):
```
Abutilon_grandifolium
Acacia_baileyana
Acacia_dealbata (1,191 images!)
Acacia_elata
Acacia_longifolia
Acacia_paradoxa
Acacia_saligna
Acacia_verticillata (1,117 images!)
... and 130+ more species
```

---

## 🚀 Workflow

### **Option A: Use Existing Embeddings (Recommended - You're Ready!)**

You already have embeddings for 141k+ images. Skip to **Step 2** below.

### **Option B: Generate New Embeddings (If Needed)**

If you want to regenerate embeddings or create them for a different dataset:

```bash
# Navigate to scripts directory
cd /Users/kryticyz/Documents/life/CISS/plantNet/scripts/images

# Activate conda environment
conda activate plantnet

# Generate embeddings for all species
python batch_generate_embeddings.py \
  /Users/kryticyz/Documents/life/CISS/plantNet/data/images/by_species \
  --output ../../data/databases/embeddings/my_new_embeddings

# Optional flags:
# --model resnet50          # Use larger model (slower but more accurate)
# --batch-size 16           # Reduce if running out of memory
# --cpu                     # Force CPU mode (if MPS has issues on macOS)
```

**What happens during embedding generation:**

```
Found 138 species directories
Using model: resnet18
Batch size: 32

Processing species: 100%|████████████| 138/138 [15:32<00:00,  6.75s/it]

Processing complete!
  Total images: 15420
  Processed: 15420
  Errors: 0

Building FAISS index...
  Index built with 15420 vectors

Computing species statistics...
  Stats computed for 138 species

Saving to data/databases/embeddings/my_new_embeddings...
  ✓ embeddings.index
  ✓ metadata.pkl
  ✓ metadata_full.pkl
  ✓ species_stats.json
  ✓ summary.json

✅ Embeddings database created successfully!
```

**Time estimates:**
- Small dataset (10 images/species × 50 species = 500 images): ~2-3 minutes
- Medium dataset (20 images/species × 200 species = 4,000 images): ~10-15 minutes
- Large dataset (100 images/species × 746 species = 74,600 images): ~30-60 minutes
- Your dataset (141,691 images): ~60-90 minutes

---

## 🌐 **STEP 2: Launch the Review Server**

Now let's start the web interface:

```bash
# Make sure you're in the right directory
cd /Users/kryticyz/Documents/life/CISS/plantNet/scripts/images

# Activate conda environment (if not already active)
conda activate plantnet

# Launch the server
python review_duplicates_v2.py \
  /Users/kryticyz/Documents/life/CISS/plantNet/data/images/by_species
```

**Expected output:**

```
✓ Loaded FAISS vector database with 141691 embeddings

============================================================
🌿 Duplicate Image Review Server (v2.0)
============================================================
Base directory: /Users/kryticyz/Documents/life/CISS/plantNet/data/images/by_species
Server running at: http://localhost:8000
============================================================

Press Ctrl+C to stop the server.
```

**Optional flags:**
```bash
# Use a different port
python review_duplicates_v2.py /path/to/by_species --port 8080

# Then open http://localhost:8080
```

---

## 🖥️ **STEP 3: Open the Web Interface**

1. **Open your browser** and go to:
   ```
   http://localhost:8000
   ```

2. You should see the **modern card-based interface**:

---

## 🎨 **UI Walkthrough**

### **Screen 1: Mode Selection** (What you see first)

```
┌─────────────────────────────────────────────────────┐
│         🌿 Plant Image Duplicate Finder             │
│       Find and remove duplicate and similar images  │
├─────────────────────────────────────────────────────┤
│                                                     │
│     What would you like to find?                   │
│                                                     │
│  ┌──────────────────┐  ┌──────────────────┐        │
│  │   🔍             │  │   🎨             │        │
│  │ Exact Duplicates │  │ Similar Images   │        │
│  │ Same image,      │  │ Different shots, │        │
│  │ different copy   │  │ same plant       │        │
│  │                  │  │                  │        │
│  │ Uses perceptual  │  │ Uses AI to detect│        │
│  │ hashing          │  │ visual similarity│        │
│  └──────────────────┘  └──────────────────┘        │
│                                                     │
│  ┌──────────────────┐                              │
│  │   ⚠️              │                              │
│  │ Outliers         │                              │
│  │ Images that      │                              │
│  │ don't belong     │                              │
│  │                  │                              │
│  │ Find images in   │                              │
│  │ wrong folder     │                              │
│  └──────────────────┘                              │
│                                                     │
│  Scan Options                                       │
│  ● All Species (Recommended)                        │
│    Scan all species folders at once                │
│  ○ Single Species                                   │
│    Scan only one species folder                    │
│    [Dropdown appears when selected]                │
│                                                     │
│         [Start Analysis]                            │
└─────────────────────────────────────────────────────┘
```

**What to do:**
1. **Click a mode card** - it will highlight with a blue border
2. **Choose scope**:
   - Keep "All Species" selected (recommended for first run)
   - Or select "Single Species" and choose from dropdown
3. **Click "Start Analysis"**

---

### **Screen 2: Results Display**

After clicking "Start Analysis", you'll see:

```
┌─────────────────────────────────────────────────────────┐
│  📊 Found 47 groups across 12 species                  │
│  15,420 images scanned                                 │
│                                                        │
│  [← Back]                                              │
├─────────────────────────────────────────────────────────┤
│                                                        │
│  Species: Acacia dealbata (3 groups)                   │
│  ┌──────────────────────────────────────────────┐     │
│  │ Group 1: 5 images                      [▼]   │     │
│  │ [Select All But Largest]                     │     │
│  ├──────────────────────────────────────────────┤     │
│  │ [Click to expand - collapsed by default]    │     │
│  └──────────────────────────────────────────────┘     │
│                                                        │
│  ┌──────────────────────────────────────────────┐     │
│  │ Group 2: 3 images                      [▼]   │     │
│  │ [Select All But Largest]                     │     │
│  └──────────────────────────────────────────────┘     │
│                                                        │
│  Species: Acacia verticillata (2 groups)               │
│  ┌──────────────────────────────────────────────┐     │
│  │ Group 1: 4 images                      [▼]   │     │
│  └──────────────────────────────────────────────┘     │
│                                                        │
├─────────────────────────────────────────────────────────┤
│  0 images selected for deletion                       │
│  [Clear Selection]  [Delete Selected]                 │
└─────────────────────────────────────────────────────────┘
```

**What you see:**
- **Results header**: Total groups and species found
- **Species sections**: Organized by species name
- **Collapsible groups**: Click header to expand/collapse
- **Sticky footer**: Always visible at bottom

---

### **Screen 3: Expanded Group View**

Click a group header to expand and see the images:

```
┌──────────────────────────────────────────────────────────┐
│  Group 1: 5 images                               [▲]    │
│  [Select All But Largest]                               │
├──────────────────────────────────────────────────────────┤
│                                                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │     ✓      │  │            │  │            │       │
│  │ ┌────────┐ │  │ ┌────────┐ │  │ ┌────────┐ │       │
│  │ │        │ │  │ │        │ │  │ │        │ │       │
│  │ │ Image  │ │  │ │ Image  │ │  │ │ Image  │ │       │
│  │ │        │ │  │ │        │ │  │ │        │ │       │
│  │ └────────┘ │  │ └────────┘ │  │ └────────┘ │       │
│  │ IMG001.jpg │  │ IMG002.jpg │  │ IMG003.jpg │       │
│  │ 2.4 MB     │  │ 1.8 MB     │  │ 1.9 MB     │       │
│  │ 🟢 Largest │  │ 🟡 Smaller │  │ 🟡 Smaller │       │
│  └────────────┘  └────────────┘  └────────────┘       │
│                                                         │
│  ┌────────────┐  ┌────────────┐                        │
│  │            │  │            │                        │
│  │ ┌────────┐ │  │ ┌────────┐ │                        │
│  │ │        │ │  │ │        │ │                        │
│  │ │ Image  │ │  │ │ Image  │ │                        │
│  │ │        │ │  │ │        │ │                        │
│  │ └────────┘ │  │ └────────┘ │                        │
│  │ IMG004.jpg │  │ IMG005.jpg │                        │
│  │ 2.1 MB     │  │ 1.7 MB     │                        │
│  │ 🟡 Smaller │  │ 🟡 Smaller │                        │
│  └────────────┘  └────────────┘                        │
└──────────────────────────────────────────────────────────┘
```

**Features:**
- **Large thumbnails**: 250px, easy to see details
- **Click image** to toggle selection (checkmark appears)
- **Click thumbnail** to view full-size preview
- **Green border**: Largest image (recommended to keep)
- **Size badges**: Shows file size and quality indicator
- **Quick select**: "Select All But Largest" button

---

### **Screen 4: Selecting Images for Deletion**

```
When you click an image:
┌────────────┐         ┌────────────┐
│     ✓      │         │            │
│ ┌────────┐ │   →     │ ┌────────┐ │
│ │ [RED]  │ │         │ │ [GRAY] │ │
│ │ BORDER │ │         │ │ BORDER │ │
│ └────────┘ │         │ └────────┘ │
│  SELECTED  │         │ NOT SELECT │
└────────────┘         └────────────┘
```

**Selection behavior:**
- **Click once**: Selects image (red border + checkmark)
- **Click again**: Deselects image
- **"Select All But Largest"**: Selects all except green-bordered image
- **Counter updates**: Footer shows "X images selected"

**Footer updates in real-time:**
```
┌─────────────────────────────────────────────────┐
│  3 images selected for deletion                │
│  [Clear Selection]  [Delete Selected]          │
└─────────────────────────────────────────────────┘
```

---

### **Screen 5: Deletion Confirmation**

Click "Delete Selected" to see:

```
┌──────────────────────────────────────────┐
│  ⚠️  Confirm Deletion                    │
├──────────────────────────────────────────┤
│                                          │
│  You're about to permanently delete:    │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │           23 images                │ │
│  │        across 5 species            │ │
│  │       Total size: 45.2 MB          │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ⚠️  This cannot be undone!             │
│                                          │
│  ▸ View list of files to delete         │
│    [Click to expand]                    │
│                                          │
│  [ Cancel ]    [Yes, Delete Files]      │
└──────────────────────────────────────────┘
```

**Safety features:**
- **Warning symbol**: Clear visual warning
- **Summary stats**: Count, species, size
- **Expandable list**: See exactly what will be deleted
- **Two buttons**: Easy to cancel
- **Cannot close by accident**: Must click Cancel or Delete

---

### **Screen 6: Deletion Progress**

After confirming:

```
┌──────────────────────────────────────────┐
│  🗑️  Deleting Files...                   │
├──────────────────────────────────────────┤
│                                          │
│  ████████████████░░░░  76% (18/23)      │
│                                          │
│  Currently deleting:                    │
│  Acacia_dealbata/IMG_042.jpg           │
│                                          │
└──────────────────────────────────────────┘
```

**Progress features:**
- **Visual progress bar**: Shows completion %
- **File count**: Current/Total
- **Current file**: Shows what's being deleted
- **Cannot be canceled**: Ensures data consistency

---

### **Screen 7: Deletion Complete**

```
┌──────────────────────────────────────────┐
│  ✅ Deletion Complete                    │
├──────────────────────────────────────────┤
│                                          │
│  Successfully deleted: 23 files         │
│  Failed: 0                              │
│  Space freed: 45.2 MB                   │
│                                          │
│  [View Summary]  [Find More Duplicates] │
└──────────────────────────────────────────┘
```

**What happens:**
- **Success message**: Clear confirmation
- **Statistics**: Files deleted, space freed
- **Auto-refresh**: Results update to remove deleted images
- **Selection cleared**: Ready for next review
- **Continue**: Can start new analysis or review more

---

## 🎯 **Common Workflows**

### **Workflow 1: Quick Cleanup - Find All Exact Duplicates**

1. Open `http://localhost:8000`
2. Click **"🔍 Exact Duplicates"** card
3. Keep **"All Species"** selected
4. Click **"Start Analysis"**
5. Wait for analysis (fast - uses perceptual hashing)
6. For each group:
   - Click header to expand
   - Click **"Select All But Largest"**
7. Click **"Delete Selected"** in footer
8. Review confirmation modal
9. Click **"Yes, Delete Files"**
10. Done! Files are deleted

**Time**: 2-5 minutes for entire dataset

---

### **Workflow 2: Find Similar Images (AI-powered)**

1. Open `http://localhost:8000`
2. Click **"🎨 Similar Images"** card
3. Keep **"All Species"** selected
4. Click **"Start Analysis"**
5. Wait for analysis (fast - uses pre-computed embeddings!)
6. Review groups:
   - These are visually similar but not identical
   - Different angles, lighting, cropping of same plant
7. Manually review each group
8. Select images you want to remove
9. Delete as usual

**Time**: Analysis is instant with embeddings! Review depends on how many groups.

---

### **Workflow 3: Single Species Deep Dive**

1. Click any mode
2. Select **"○ Single Species"**
3. Choose species from dropdown (e.g., "Acacia dealbata")
4. Click **"Start Analysis"**
5. Review only that species
6. Perfect for cleaning up one species at a time

**Use case**: When you know a particular species has issues

---

### **Workflow 4: Find Outliers (Wrong Folder)**

1. Click **"⚠️ Outliers"** card
2. Select **"All Species"**
3. Click **"Start Analysis"**
4. Review images that are very different from others in their folder
5. These might be:
   - Wrong species in folder
   - Non-plant images
   - Very poor quality images
6. Manually review before deleting

**Use case**: Data quality check

---

## 💡 **Tips & Tricks**

### **Tip 1: Start with "All Species" Mode**
- Faster than running species one-by-one
- Get overview of entire dataset
- See which species have most duplicates

### **Tip 2: Use "Select All But Largest"**
- Automatically keeps the highest quality image
- Safe default for most cases
- Saves time vs. manual selection

### **Tip 3: Preview Before Deleting**
- Click image thumbnail to see full-size
- Use this to verify duplicates
- Helps catch false positives

### **Tip 4: Work in Batches**
- Review 5-10 groups at a time
- Delete batch
- Continue to next groups
- Less overwhelming for large datasets

### **Tip 5: Check "View list" in Confirmation**
- Always expand the file list before confirming
- Double-check what will be deleted
- Catch any mistakes

### **Tip 6: Start with Exact Duplicates**
- These are safest to delete
- Clear-cut duplicates
- Save "Similar Images" for later review

### **Tip 7: Mobile-Friendly**
- Works on tablets!
- Good for reviewing on iPad
- Touch-friendly interface

---

## 🔧 **Troubleshooting**

### **Problem: Server won't start**

```bash
# Check if port is already in use
lsof -i :8000

# If yes, kill the process or use different port
python review_duplicates_v2.py /path/to/images --port 8080
```

### **Problem: "FAISS not available" message**

```bash
# Install FAISS
conda install -c conda-forge faiss-cpu

# Or regenerate embeddings
python batch_generate_embeddings.py /path/to/images
```

### **Problem: Images not loading**

- Check browser console for errors (F12)
- Verify image paths in your dataset
- Make sure you're using the correct base directory path

### **Problem: Analysis is slow**

- **Exact Duplicates**: Should be fast (seconds)
- **Similar Images**: 
  - WITH embeddings: Instant!
  - WITHOUT embeddings: Slow (computes on-the-fly)
- **Solution**: Generate embeddings first (Step 1)

### **Problem: Too many groups to review**

- Use "Single Species" mode
- Work on one species at a time
- Start with species that have most duplicates

---

## 📈 **Expected Results**

Based on your dataset of **141,691 images** across **746 species**:

### **Exact Duplicates**
- **Typical**: 5-15% duplicate rate
- **Expected groups**: 500-2,000 groups
- **Images to delete**: 7,000-21,000 files
- **Space saved**: 10-30 GB (depending on image size)

### **Similar Images**
- **Typical**: 10-25% similarity rate  
- **Expected groups**: 1,000-5,000 groups
- **Needs manual review**: These aren't exact duplicates
- **Use case**: Different angles of same plant

### **Outliers**
- **Typical**: 1-5% outlier rate
- **Expected groups**: 100-500 groups
- **Needs careful review**: May be legitimate
- **Use case**: Quality control

---

## ✅ **Summary Checklist**

- [x] ✅ Embeddings generated (141,691 images)
- [ ] Launch review server
- [ ] Open http://localhost:8000
- [ ] Select mode (Exact Duplicates recommended first)
- [ ] Choose "All Species"
- [ ] Click "Start Analysis"
- [ ] Review groups
- [ ] Select images for deletion
- [ ] Confirm deletion
- [ ] Space saved!

---

## 🎉 **You're Ready!**

Your system is all set up with:
- ✅ 141,691 images indexed
- ✅ 746 species organized
- ✅ Modern web UI ready
- ✅ FAISS embeddings for instant searches

**Next step**: 
```bash
cd /Users/kryticyz/Documents/life/CISS/plantNet/scripts/images
conda activate plantnet
python review_duplicates_v2.py /Users/kryticyz/Documents/life/CISS/plantNet/data/images/by_species
```

Then open `http://localhost:8000` and start cleaning up your dataset! 🚀
