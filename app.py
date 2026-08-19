import streamlit as st
import sqlite3
from pathlib import Path
from PIL import Image, ImageOps
import pandas as pd
import uuid

BASE = Path(__file__).parent
DB = BASE / "data" / "sanora.db"
GEN = BASE / "generated_images"
GEN.mkdir(exist_ok=True)
DB.parent.mkdir(exist_ok=True)

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = conn()
    c.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, category TEXT,
        material TEXT, color TEXT, pack INTEGER, cost REAL, packaging REAL,
        price REAL, hsn TEXT, title TEXT, description TEXT, keywords TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS experiments(
        id INTEGER PRIMARY KEY AUTOINCREMENT, product TEXT, variant TEXT,
        occupancy REAL, background TEXT, shipping REAL, price REAL,
        notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS competitors(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, url TEXT,
        category TEXT, price REAL, pack INTEGER, rating REAL, reviews INTEGER,
        notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    c.commit(); c.close()

def rows(table):
    c=conn()
    r=c.execute(f"SELECT * FROM {table} ORDER BY id DESC").fetchall()
    c.close()
    return [dict(x) for x in r]

def listing(name, ptype, category, material, color, pack, target, size, design, features, occasion, use, brand, limit):
    ptype = ptype or name or "Hair Accessory"
    title = " ".join(x for x in [material, ptype, color, f"Pack of {pack}", f"for {target}" if target else ""] if x)
    desc = (f"Product: {title}\nBrand: {brand}\nMaterial: {material or 'Not specified'}\n"
            f"Color: {color or 'Not specified'}\nPack of: {pack}\nDesign: {design or 'Not specified'}\n"
            f"Size: {size or 'Standard'}\nSuitable For: {target or 'Women & Girls'}\n"
            f"Features: {features or 'Soft, lightweight, comfortable and reusable'}\n"
            f"Use: {use or 'Everyday styling'}\nOccasion: {occasion or 'Daily wear, outings and gifting'}\n"
            f"Package Contains: {pack} {ptype}")[:limit]
    kws=[material, ptype, color, f"{ptype} for women", f"{ptype} for girls",
         "hair accessories", "hair ties", "hair bands", f"{ptype} pack of {pack}"]
    kws=", ".join(dict.fromkeys(x.strip() for x in kws if x))
    return title, desc, features or "Soft, lightweight, comfortable and reusable", kws, {
        "Brand":brand,"Category":category,"Material":material,"Color":color,
        "Pack":pack,"Size":size,"Design":design,"Ideal For":target,"Occasion":occasion}

def analyze(title, desc, price, cost, category, material, color, pack, keywords, image):
    s={}
    tl=len(title.strip())
    s["Title SEO"]=min(100,45+(20 if 25<=tl<=110 else 5)+sum(7 for x in [material,color,str(pack)] if x and x.lower() in title.lower()))
    s["Description"]=min(100,40+len(desc.strip())/10)
    s["Keywords"]=min(100,len([x for x in keywords.split(",") if x.strip()])*5)
    s["Attributes"]=sum(bool(x) for x in [category,material,color,pack])*25
    s["Pricing"]=85 if price>=cost*1.5 and price>0 else 60 if price>cost else 20
    s["Profitability"]=90 if price>=cost*2 else 70 if price>=cost*1.5 else 35
    s["Image"]=85 if image else 40
    improvements=[]
    if tl<25: improvements.append("Make the title more descriptive.")
    if tl>120: improvements.append("Shorten the title and remove repetition.")
    if len(desc.strip())<80: improvements.append("Add clear product specifications.")
    if len([x for x in keywords.split(",") if x.strip()])<8: improvements.append("Add more relevant keywords.")
    if not image: improvements.append("Add a clear primary image.")
    if price<=cost: improvements.append("Selling price is not above cost.")
    strengths=[f"{k} is strong." for k,v in s.items() if v>=80]
    return {k:int(v) for k,v in s.items()}, round(sum(s.values())/len(s)), strengths, improvements

def profit(selling, product, packaging, other, gst, tcs, tds, fixed, rr, rc):
    deductions=selling*(gst+tcs+tds)/100+fixed
    settlement=selling-deductions
    total=product+packaging+other
    p=settlement-total
    expected=p-(rr/100*rc)
    return settlement,total,p,expected,(p/selling*100 if selling else 0)

def variants(file):
    img=Image.open(file).convert("RGBA")
    side=max(img.size)
    sq=Image.new("RGBA",(side,side),(255,255,255,255))
    sq.alpha_composite(img,((side-img.width)//2,(side-img.height)//2))
    specs=[("White 45%",.45,(255,255,255,255)),("White 55%",.55,(255,255,255,255)),
           ("White 65%",.65,(255,255,255,255)),("White 70%",.70,(255,255,255,255)),
           ("Light Grey 55%",.55,(248,248,248,255)),("Light Beige 55%",.55,(248,244,238,255))]
    out=[]
    for name,occ,bg in specs:
        canvas=Image.new("RGBA",(1200,1200),bg)
        fitted=ImageOps.contain(sq,(int(1200*occ),int(1200*occ)),Image.Resampling.LANCZOS)
        canvas.alpha_composite(fitted,((1200-fitted.width)//2,(1200-fitted.height)//2))
        path=GEN/f"{uuid.uuid4().hex}.png"
        canvas.convert("RGB").save(path,"PNG",optimize=True)
        out.append((name,int(occ*100),path))
    return out

init_db()
st.set_page_config(page_title="Sanora Seller Studio", page_icon="🎀", layout="wide")
st.title("🎀 Sanora Seller Studio")
st.caption("Personal Meesho catalog, pricing and image-testing workspace")

page=st.sidebar.radio("Navigate",[
    "Dashboard","SEO Listing Generator","Catalog Analyzer","Image Optimizer",
    "Profit Calculator","Image Experiments","Product Library","Competitor Tracker"])

if page=="Dashboard":
    p=rows("products"); e=rows("experiments"); c=rows("competitors")
    a,b,d,f=st.columns(4)
    a.metric("Products",len(p)); b.metric("Image experiments",len(e)); d.metric("Competitors",len(c))
    f.metric("Avg selling price",f"₹{round(pd.DataFrame(p)['price'].mean(),2) if p else 0}")
    st.info("Workflow: generate listing → calculate profit → create image variants → test on Meesho → record the actual shipping result.")
    if p: st.dataframe(pd.DataFrame(p),use_container_width=True,hide_index=True)

elif page=="SEO Listing Generator":
    st.header("📝 SEO Listing Generator")
    with st.form("seo"):
        a,b=st.columns(2)
        with a:
            name=st.text_input("Product name"); ptype=st.text_input("Product type")
            category=st.text_input("Category"); material=st.text_input("Material")
            color=st.text_input("Color"); pack=st.number_input("Pack quantity",1,100,2)
            brand=st.text_input("Brand","Sanora")
        with b:
            target=st.text_input("Target customer","Women & Girls"); size=st.text_input("Size","Standard")
            design=st.text_input("Design"); features=st.text_area("Features")
            occasion=st.text_input("Occasion"); use=st.text_input("Use case")
            limit=st.number_input("Description limit",300,1400,1400)
        go=st.form_submit_button("Generate Listing",type="primary")
    if go:
        st.session_state["listing"]=listing(name,ptype,category,material,color,int(pack),target,size,design,features,occasion,use,brand,int(limit))
    if "listing" in st.session_state:
        t,d,f,k,attrs=st.session_state["listing"]
        st.text_area("Product Title",t,height=70); st.text_area("Description",d,height=220)
        st.text_area("Key Features",f,height=100); st.text_area("Search Keywords",k,height=100)
        st.json(attrs)
        st.caption("HSN/category classification must be verified before publishing.")

elif page=="Catalog Analyzer":
    st.header("🔎 Catalog Analyzer")
    with st.form("an"):
        title=st.text_input("Product title"); desc=st.text_area("Description")
        price=st.number_input("Selling price",0.0,100000.0,59.0); cost=st.number_input("Product + packaging cost",0.0,100000.0,24.0)
        category=st.text_input("Category"); material=st.text_input("Material"); color=st.text_input("Color")
        pack=st.number_input("Pack quantity",1,100,2); keywords=st.text_area("Keywords, comma separated")
        image=st.file_uploader("Primary image",type=["png","jpg","jpeg","webp"])
        go=st.form_submit_button("Analyze",type="primary")
    if go:
        scores,overall,strengths,improvements=analyze(title,desc,price,cost,category,material,color,int(pack),keywords,image)
        st.metric("Sanora Catalog Quality Score",f"{overall}/100")
        cols=st.columns(len(scores))
        for col,(k,v) in zip(cols,scores.items()): col.metric(k,f"{v}/100")
        for x in strengths: st.success(x)
        for x in improvements: st.warning(x)

elif page=="Image Optimizer":
    st.header("📸 Image Optimizer")
    st.caption("Creates legitimate composition variants. It does not guarantee a lower Meesho shipping slab.")
    f=st.file_uploader("Upload product image",type=["png","jpg","jpeg","webp"])
    if f:
        st.image(f,width=350)
        if st.button("Generate variants",type="primary"): st.session_state["vars"]=variants(f)
    for i,(name,occ,path) in enumerate(st.session_state.get("vars",[])):
        col=st.columns(3)[i%3]; col.image(str(path),caption=f"{name} • target {occ}%")
        col.download_button("Download",path.read_bytes(),path.name,"image/png",key=f"dl{i}")

elif page=="Profit Calculator":
    st.header("💰 Profit Calculator")
    a,b=st.columns(2)
    with a:
        selling=st.number_input("Selling price",0.0,100000.0,59.0)
        product=st.number_input("Product cost",0.0,100000.0,20.0)
        packaging=st.number_input("Packaging cost",0.0,100000.0,4.0)
        other=st.number_input("Other cost",0.0,100000.0,0.0)
        rr=st.number_input("Expected return/RTO rate %",0.0,100.0,5.0)
        rc=st.number_input("Cost per return/RTO",0.0,100000.0,20.0)
    with b:
        gst=st.number_input("GST/other deduction %",0.0,100.0,0.0)
        tcs=st.number_input("TCS %",0.0,100.0,0.0); tds=st.number_input("TDS %",0.0,100.0,0.0)
        fixed=st.number_input("Other fixed deduction",0.0,100000.0,0.0)
    settlement,total,p,expected,margin=profit(selling,product,packaging,other,gst,tcs,tds,fixed,rr,rc)
    a,b,c,d=st.columns(4)
    a.metric("Settlement",f"₹{settlement:.2f}"); b.metric("Profit/order",f"₹{p:.2f}")
    c.metric("Expected after returns",f"₹{expected:.2f}"); d.metric("Margin",f"{margin:.1f}%")

elif page=="Image Experiments":
    st.header("🧪 Image Experiments")
    st.caption("Record the actual shipping value shown by Meesho after testing each image.")
    with st.form("exp"):
        product=st.text_input("Product"); variant=st.text_input("Variant","White 55%")
        occ=st.number_input("Estimated occupancy %",0.0,100.0,55.0)
        bg=st.selectbox("Background",["White","Light Grey","Light Beige","Other"])
        shipping=st.number_input("Meesho shipping",0.0,100000.0,0.0)
        price=st.number_input("Meesho price",0.0,100000.0,59.0); notes=st.text_area("Notes")
        save=st.form_submit_button("Save",type="primary")
    if save:
        c=conn(); c.execute("INSERT INTO experiments(product,variant,occupancy,background,shipping,price,notes) VALUES(?,?,?,?,?,?,?)",(product,variant,occ,bg,shipping,price,notes)); c.commit(); c.close(); st.success("Saved.")
    e=rows("experiments")
    if e:
        df=pd.DataFrame(e); st.dataframe(df,use_container_width=True,hide_index=True)
        if len(df)>=2:
            st.subheader("Average shipping by occupancy")
            bins=[0,40,50,60,70,80,101]; labels=["<40","40-49","50-59","60-69","70-79","80+"]
            df["band"]=pd.cut(df["occupancy"],bins=bins,labels=labels,right=False)
            st.dataframe(df.groupby("band",observed=False)["shipping"].mean().reset_index(),use_container_width=True,hide_index=True)

elif page=="Product Library":
    st.header("📦 Product Library")
    with st.form("prod"):
        name=st.text_input("Product name"); category=st.text_input("Category"); material=st.text_input("Material")
        color=st.text_input("Color"); pack=st.number_input("Pack",1,100,2); cost=st.number_input("Product cost",0.0,100000.0,20.0)
        packaging=st.number_input("Packaging cost",0.0,100000.0,4.0); price=st.number_input("Selling price",0.0,100000.0,59.0)
        hsn=st.text_input("HSN"); title=st.text_input("Listing title"); desc=st.text_area("Description"); keywords=st.text_area("Keywords")
        save=st.form_submit_button("Save product",type="primary")
    if save:
        c=conn(); c.execute("""INSERT INTO products(name,category,material,color,pack,cost,packaging,price,hsn,title,description,keywords)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",(name,category,material,color,int(pack),cost,packaging,price,hsn,title,desc,keywords)); c.commit(); c.close(); st.success("Saved.")
    p=rows("products")
    if p:
        df=pd.DataFrame(p); st.dataframe(df,use_container_width=True,hide_index=True)
        st.download_button("Export CSV",df.to_csv(index=False).encode(),"sanora_products.csv","text/csv")

elif page=="Competitor Tracker":
    st.header("🔍 Competitor Tracker")
    with st.form("comp"):
        name=st.text_input("Competitor product"); url=st.text_input("Product URL"); category=st.text_input("Category")
        price=st.number_input("Price",0.0,100000.0,0.0); pack=st.number_input("Pack",1,100,1)
        rating=st.number_input("Rating",0.0,5.0,0.0); reviews=st.number_input("Reviews",0,10000000,0); notes=st.text_area("Notes")
        save=st.form_submit_button("Save competitor",type="primary")
    if save:
        c=conn(); c.execute("""INSERT INTO competitors(name,url,category,price,pack,rating,reviews,notes)
        VALUES(?,?,?,?,?,?,?,?)""",(name,url,category,price,int(pack),rating,int(reviews),notes)); c.commit(); c.close(); st.success("Saved.")
    x=rows("competitors")
    if x: st.dataframe(pd.DataFrame(x),use_container_width=True,hide_index=True)
