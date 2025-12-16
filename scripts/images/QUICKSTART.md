# 🚀 Quick Start Guide - Duplicate Review UI

## ⚡ TL;DR - Start Reviewing Now!

```bash
cd /Users/kryticyz/Documents/life/CISS/plantNet/scripts/images
conda activate plantnet
python review_duplicates_v2.py \
  /Users/kryticyz/Documents/life/CISS/plantNet/data/images/by_species
```

Then open: **http://localhost:8000**

---

## 📋 Your Dataset Status

✅ **Ready to go!**
- **Images**: 141,691 indexed
- **Species**: 746 
- **Embeddings**: Pre-computed (instant searches!)
- **Status**: Everything set up

---

## 🎯 First-Time Workflow (5 minutes)

### 1. Launch Server
```bash
cd /Users/kryticyz/Documents/life/CISS/plantNet/scripts/images
conda activate plantnet
python review_duplicates_v2.py \
  /Users/kryticyz/Documents/life/CISS/plantNet/data/images/by_species
```

### 2. Open Browser
Go to: `http://localhost:8000`

### 3. Select Mode
Click: **🔍 Exact Duplicates** (safest to start)

### 4. Choose Scope
Keep: **● All Species (Recommended)**

### 5. Start
Click: **[Start Analysis]**

### 6. Review Results
- Click group header to expand
- Click **[Select All But Largest]**
- Repeat for a few groups

### 7. Delete
- Click **[Delete Selected]** in footer
- Review confirmation
- Click **[Yes, Delete Files]**

### 8. Done! 🎉
Files are deleted, space is freed!

---

## 🎨 Three Modes Explained

### 🔍 Exact Duplicates
- **What**: Same image, different copy
- **How**: Perceptual hashing
- **Speed**: Very fast (seconds)
- **Safety**: ✅ Safe to delete
- **Use**: First cleanup pass

### 🎨 Similar Images  
- **What**: Different shots, same plant
- **How**: AI-powered CNN similarity
- **Speed**: Instant (with embeddings)
- **Safety**: ⚠️ Needs review
- **Use**: Advanced cleanup

### ⚠️ Outliers
- **What**: Images that don't belong
- **How**: Low similarity threshold
- **Speed**: Instant (with embeddings)
- **Safety**: ⚠️ Careful review needed
- **Use**: Quality control

---

## 💡 Quick Tips

1. **Start simple**: Use "Exact Duplicates" first
2. **Use quick select**: "Select All But Largest" button
3. **Preview images**: Click thumbnail for full-size
4. **Work in batches**: Review 5-10 groups at a time
5. **Check before delete**: Expand file list in confirmation

---

## 🔧 Common Issues

**Server won't start?**
```bash
# Use different port
python review_duplicates_v2.py /path/to/images --port 8080
```

**"FAISS vector database not available"?**

This means embeddings weren't found. The server will show where it searched. Solutions:

1. **Have you generated embeddings?**
   ```bash
   python batch_generate_embeddings.py /path/to/by_species
   ```

2. **Are embeddings in the right location?**
   Check the output - it shows exactly where it looked:
   ```
   ⚠️  No embeddings found. Searched:
      1. /full/path/to/data/databases/embeddings
      2. /current/directory/data/databases/embeddings
   ```

3. **Specify path manually:**
   ```bash
   python review_duplicates_v2.py /path/to/images \
     --embeddings /path/to/embeddings
   ```

4. **Check files exist:**
   ```bash
   ls data/databases/embeddings/embeddings.index
   ls data/databases/embeddings/metadata.pkl
   ```

**Need help?**
- See: `WALKTHROUGH.md` for detailed guide
- See: `IMPLEMENTATION_COMPLETE.md` for technical details

---

## 📱 Mobile Access

The UI works on tablets! 
1. Find your computer's IP: `ifconfig | grep inet`
2. On tablet browser: `http://YOUR_IP:8000`

---

## ⌨️ Keyboard Shortcuts

- **Escape**: Close modals/previews
- **Tab**: Navigate elements
- **Enter/Space**: Activate buttons

---

## 🎯 Expected Results

For your 141k image dataset:

**Exact Duplicates:**
- Groups: ~500-2,000
- Can delete: ~7k-21k images
- Space saved: ~10-30 GB

**Similar Images:**
- Groups: ~1k-5k
- Needs review: Yes
- Use case: Different angles

---

## ✅ You're All Set!

Everything is ready. Just run the command and start cleaning! 🚀

**Full walkthrough**: See `WALKTHROUGH.md`  
**Technical docs**: See `IMPLEMENTATION_COMPLETE.md`
