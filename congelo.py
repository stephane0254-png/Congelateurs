<!DOCTYPE html>
<html>
  <head>
    <base target="_top">
    <style>
      body { font-family: 'Segoe UI', Arial; padding: 15px; background-color: #f0f2f5; color: #333; }
      .card { background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
      input, select, button { width: 100%; padding: 10px; margin: 5px 0 15px 0; border-radius: 5px; border: 1px solid #ddd; box-sizing: border-box; }
      button { background-color: #007bff; color: white; border: none; font-weight: bold; cursor: pointer; }
      button.btn-qty { width: 30px; height: 30px; padding: 0; margin: 0 5px; background-color: #6c757d; }
      button.btn-del { background-color: #dc3545; width: auto; padding: 5px 8px; font-size: 12px; }
      table { width: 100%; border-collapse: collapse; margin-top: 10px; }
      td { padding: 10px 5px; border-bottom: 1px solid #eee; }
      .badge { font-size: 10px; padding: 2px 5px; border-radius: 4px; background: #e9ecef; margin-right: 3px; display: inline-block; margin-top: 3px;}
      .alerte-orange { border-left: 5px solid orange; background-color: #fffaf0; }
      .alerte-rouge { border-left: 5px solid red; background-color: #fff5f5; }
      .compteur-urgence { background: #ff4757; color: white; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 15px; font-weight: bold; display: none; }
      .filter-group { display: flex; gap: 8px; margin-bottom: 5px; }
      .filter-group select { margin-bottom: 5px; }
    </style>
  </head>
  <body>
    <h3>❄️ Mon Congélateur</h3>
    
    <div class="card">
      <input type="text" id="produit" placeholder="Nom du produit">
      <div class="filter-group">
        <select id="categorie"><option>Plat cuisiné</option><option>Surgelé</option><option>Autre</option></select>
        <select id="contenant">
          <option>Couvercle rouge</option>
          <option>Couvercle vert</option>
          <option>Grand bleu</option>
          <option>Petit bleu</option>
          <option>Plastique blanc</option>
          <option>Préemballage</option>
          <option>Pyrex</option>
          <option>Tupperware</option>
          <option>Verre Carré</option>
          <option>Moyen bleu</option>
          <option>Sachet</option>
        </select>
      </div>
      <div class="filter-group">
        <select id="emplacement"><option>Cuisine</option><option>Buanderie</option></select>
        <input type="number" id="quantite" value="1" style="width: 80px;">
      </div>
      <button onclick="ajouter()">Ajouter au stock</button>
    </div>

    <div class="card">
      <div id="alerteUrgence" class="compteur-urgence"></div>
      <strong>🔍 Rechercher / Filtrer</strong>
      <input type="text" id="recherche" placeholder="Nom du produit..." oninput="filtrerStock()">
      
      <div class="filter-group">
        <select id="filtreCat" onchange="filtrerStock()">
          <option value="">Toutes catégories</option>
          <option>Plat cuisiné</option>
          <option>Surgelé</option>
          <option>Autre</option>
        </select>
        <select id="filtreLoc" onchange="filtrerStock()">
          <option value="">Tous les lieux</option>
          <option>Cuisine</option>
          <option>Buanderie</option>
        </select>
      </div>

      <div id="listeStock">Chargement...</div>
    </div>

    <script>
      let stockComplet = [];

      window.onload = function() {
        google.script.run.withSuccessHandler(res => { stockComplet = res; filtrerStock(); }).obtenirStock();
      };

      function ajouter() {
        var d = {
          produit: document.getElementById('produit').value,
          categorie: document.getElementById('categorie').value,
          contenant: document.getElementById('contenant').value,
          quantite: document.getElementById('quantite').value,
          emplacement: document.getElementById('emplacement').value
        };
        if(!d.produit) { alert("Nom vide"); return; }
        google.script.run.withSuccessHandler(res => { stockComplet = res; filtrerStock(); }).ajouterAliment(d);
        document.getElementById('produit').value = "";
      }

      function changerQte(idx, q, m) { google.script.run.withSuccessHandler(res => { stockComplet = res; filtrerStock(); }).modifierQuantite(idx, q + m); }
      function supprimer(idx) { if(confirm("Supprimer ?")) google.script.run.withSuccessHandler(res => { stockComplet = res; filtrerStock(); }).supprimerLigne(idx); }

      function filtrerStock() {
        const t = document.getElementById('recherche').value.toLowerCase();
        const fCat = document.getElementById('filtreCat').value;
        const fLoc = document.getElementById('filtreLoc').value;

        let resultat = stockComplet.filter(i => {
          const matchT = i.produit.toLowerCase().includes(t);
          const matchC = fCat === "" || i.cat === fCat;
          const matchL = fLoc === "" || i.loc === fLoc;
          return matchT && matchC && matchL;
        });
        
        resultat.sort((a, b) => new Date(a.date) - new Date(b.date));
        afficher(resultat);
      }

      function afficher(stock) {
        var h = '<table>';
        const maintenant = new Date();
        let nbUrgence = 0;

        stock.forEach(item => {
          const dateCongel = new Date(item.date);
          const mois = (maintenant - dateCongel) / (1000 * 60 * 60 * 24 * 30.44);
          let classeAlerte = "";
          
          if (mois >= 6) { classeAlerte = "alerte-rouge"; nbUrgence++; }
          else if (mois >= 3) { classeAlerte = "alerte-orange"; }

          h += `<tr class="${classeAlerte}">` +
            `<td><b>${item.produit}</b><br>` +
            `<span class="badge">${item.cat}</span>` +
            `<span class="badge" style="background:#d1ecf1">${item.contenant}</span>` +
            `<span class="badge" style="background:#fff3cd">${item.loc}</span></td>` +
            `<td style="white-space:nowrap; text-align:right;">` +
              `<button class="btn-qty" onclick="changerQte(${item.index},${item.qte},-1)">-</button>` +
              `<b>${item.qte}</b>` +
              `<button class="btn-qty" onclick="changerQte(${item.index},${item.qte},1)">+</button>` +
            `</td>` +
            `<td><button class="btn-del" onclick="supprimer(${item.index})">🗑️</button></td>` +
          `</tr>`;
        });

        const bandeau = document.getElementById('alerteUrgence');
        if (nbUrgence > 0) {
          bandeau.style.display = "block";
          bandeau.innerHTML = `⚠️ ${nbUrgence} produit(s) à consommer (6 mois+)`;
        } else {
          bandeau.style.display = "none";
        }

        document.getElementById('listeStock').innerHTML = stock.length === 0 ? "Aucun produit trouvé." : h + '</table>';
      }
    </script>
  </body>
</html>
