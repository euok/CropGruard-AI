# -*- coding: utf-8 -*-
"""
CropGuard AI - disease & treatment knowledge base (DATA ONLY).

Edit this file to add or correct diseases. Keep wording short and practical.
Every text is a tuple (English, Kiswahili, French).  Advice is intentionally
expressed as *active ingredients and practices*, never brand names or dose
rates, because registrations, rates and pre-harvest intervals differ by country
and product label.  Have a plant pathologist / extension officer review this
file before you rely on it in production.

Structure
---------
CROP_FAMILIES : crop family -> display labels + synonyms (used to map the crop the
                farmer selects, and the crop prefix of the model classes, to one family)
ACTIONS       : action code -> (en, sw, fr) sentence, reused by many diseases
DISEASES      : disease key -> entry (names, how to recognise it, ordered action codes)
"""

LANGS = ("en", "sw", "fr")

# ----------------------------------------------------------------------------
# Crop families
# ----------------------------------------------------------------------------
# family: (label en, label sw, label fr, synonyms)
CROP_FAMILIES = {
    "maize": ("Maize", "Mahindi", "Maïs",
              ["maize", "corn", "corn maize", "mahindi", "mais"]),
    "potato": ("Irish potato", "Viazi mviringo", "Pomme de terre",
               ["potato", "potatoes", "irish potato", "viazi mviringo", "pomme de terre"]),
    "tomato": ("Tomato", "Nyanya", "Tomate",
               ["tomato", "tomatoes", "nyanya", "tomate", "tomates"]),
    "beans": ("Beans", "Maharagwe", "Haricot",
              ["bean", "beans", "common bean", "maharagwe", "haricot", "haricots"]),
    "groundnut": ("Groundnut", "Karanga", "Arachide",
                  ["groundnut", "groundnuts", "peanut", "peanuts", "karanga", "arachide"]),
    "tea": ("Tea", "Chai", "Thé", ["tea", "chai", "the"]),
    "coffee": ("Coffee", "Kahawa", "Café", ["coffee", "kahawa", "cafe"]),
    "banana": ("Banana / plantain", "Ndizi", "Banane / plantain",
               ["banana", "bananas", "plantain", "plantains", "ndizi", "banane", "bananier"]),
    "brassica": ("Kale / cabbage", "Sukuma wiki / kabichi", "Chou",
                 ["kale", "kales", "cabbage", "sukuma", "sukuma wiki", "brassica", "collard", "chou"]),
    "wheat": ("Wheat", "Ngano", "Blé", ["wheat", "ngano", "ble"]),
    "rice": ("Rice", "Mpunga", "Riz", ["rice", "mpunga", "riz"]),
    "cassava": ("Cassava", "Mhogo", "Manioc", ["cassava", "mhogo", "manioc"]),
    "yam": ("Yam", "Viazi vikuu", "Igname", ["yam", "yams", "igname"]),
    "cowpea": ("Cowpea", "Kunde", "Niébé", ["cowpea", "cowpeas", "kunde", "niebe"]),
    "cocoa": ("Cocoa", "Kakao", "Cacao", ["cocoa", "cacao", "kakao"]),
    "spiderplant": ("Spider plant", "Chinsaka", "Cléome", ["spider plant", "chinsaka"]),
    "nightshade": ("African nightshade", "Managu", "Morelle noire",
                   ["nightshade", "african nightshade", "managu"]),
}

# words that mean "no specific crop" in the crop drop-down
GENERAL_CROP_WORDS = ["other", "general", "mingine", "jumla", "autre", "generale"]

# ----------------------------------------------------------------------------
# Reusable actions  (en, sw, fr)
# ----------------------------------------------------------------------------
ACTIONS = {
    # ---- first response -------------------------------------------------
    "ISOLATE": (
        "Handle healthy plants first, then affected ones; do not carry the problem on wet hands, tools or clothes.",
        "Shughulikia mimea yenye afya kwanza, kisha iliyoathirika; usibebe ugonjwa kwa mikono, vifaa au nguo zenye unyevu.",
        "Travaillez d'abord les plantes saines, puis les plantes atteintes ; ne transportez pas le problème avec des mains, outils ou vêtements mouillés."),
    "REMOVE_LEAVES": (
        "Remove the affected leaves and destroy them (burn or bury deeply); do not compost them.",
        "Ondoa majani yaliyoathirika na uyaharibu (choma au zika chini kabisa); usiyaweke kwenye mboji.",
        "Retirez les feuilles atteintes et détruisez-les (brûlez ou enfouissez profondément) ; ne les mettez pas au compost."),
    "UPROOT_DESTROY": (
        "Uproot affected plants, carry them out in a bag and burn or bury them away from the field; do not compost.",
        "Ng'oa mimea iliyoathirika, ibebe kwenye mfuko, kisha uichome au uizike mbali na shamba; usiiweke kwenye mboji.",
        "Arrachez les plants atteints, sortez-les dans un sac et brûlez-les ou enfouissez-les loin du champ ; pas de compostage."),
    "REMOVE_MAT": (
        "Cut infected plants at ground level, chop them up and burn or bury the pieces; follow your national extension protocol.",
        "Kata mimea iliyoambukizwa usawa wa ardhi, ikate vipande vidogo kisha uchome au uzike; fuata maelekezo ya ugani ya nchi yako.",
        "Coupez les plants infectés au ras du sol, hachez-les et brûlez ou enfouissez les morceaux ; suivez le protocole national de vulgarisation."),
    "DISINFECT_TOOLS": (
        "Disinfect knives, hoes and pruning tools between plants (flame, 70% alcohol, or 1 part household bleach to 9 parts water).",
        "Safisha na kuua vijidudu kwenye visu, jembe na vifaa vya kupogoa kati ya mmea mmoja na mwingine (moto, pombe 70%, au sehemu 1 ya bleach kwa sehemu 9 za maji).",
        "Désinfectez couteaux, houes et sécateurs entre deux plants (flamme, alcool à 70 %, ou 1 volume d'eau de Javel pour 9 volumes d'eau)."),
    "SCOUT": (
        "Inspect the whole field every 2-3 days (more often in wet weather) and note how fast the problem is spreading.",
        "Kagua shamba zima kila baada ya siku 2-3 (mara nyingi zaidi wakati wa mvua) na uandike jinsi tatizo linavyoenea.",
        "Inspectez tout le champ tous les 2 à 3 jours (plus souvent par temps humide) et notez la vitesse de propagation."),
    "CLEAR_WEEDS": (
        "Clear weeds and volunteer plants in and around the field; they can harbour the disease or the insects that spread it.",
        "Ondoa magugu na mimea iliyoota yenyewe ndani na karibu na shamba; yanaweza kuhifadhi ugonjwa au wadudu wanaoueneza.",
        "Éliminez les mauvaises herbes et les repousses dans et autour du champ ; elles peuvent abriter la maladie ou les insectes qui la transmettent."),
    "WASH_HANDS": (
        "Wash hands with soap before handling plants; some viruses spread on hands and tools (especially after handling tobacco).",
        "Osha mikono kwa sabuni kabla ya kushika mimea; baadhi ya virusi huenea kwa mikono na vifaa (hasa baada ya kushika tumbaku).",
        "Lavez-vous les mains au savon avant de toucher les plants ; certains virus se transmettent par les mains et les outils (surtout après avoir manipulé du tabac)."),
    "RESTRICT_MOVEMENT": (
        "Do not move soil, plants, cuttings or tools from this field to other farms; wash boots and equipment before leaving.",
        "Usihamishe udongo, mimea, vipandikizi au vifaa kutoka shamba hili kwenda mashamba mengine; osha buti na vifaa kabla ya kuondoka.",
        "Ne déplacez ni terre, ni plants, ni boutures, ni outils de ce champ vers d'autres exploitations ; lavez bottes et matériel avant de partir."),
    "REPORT": (
        "Report suspected cases to your local agricultural extension office: this problem can spread quickly between farms.",
        "Ripoti kesi zinazoshukiwa kwa ofisi ya ugani ya eneo lako: tatizo hili linaweza kuenea haraka kati ya mashamba.",
        "Signalez les cas suspects au service de vulgarisation agricole local : ce problème peut se propager vite d'une exploitation à l'autre."),
    "CONFIRM": (
        "If the symptoms do not match your plants or are spreading fast, take fresh photos and visit your extension officer or plant clinic before spraying.",
        "Kama dalili hazilingani na mimea yako au zinaenea haraka, piga picha mpya na umwone afisa ugani au kliniki ya mimea kabla ya kunyunyizia dawa.",
        "Si les symptômes ne correspondent pas à vos plants ou se propagent vite, prenez de nouvelles photos et consultez votre conseiller agricole ou une clinique des plantes avant de traiter."),
    "SAND_WHORL": (
        "On young maize, hand-pick egg masses and larvae; dry sand, soil or wood ash dropped into the whorl can also reduce larvae.",
        "Kwenye mahindi machanga, okota mayai na viwavi kwa mkono; mchanga mkavu, udongo au majivu yakidondoshwa kwenye shina la majani (whorl) yanaweza pia kupunguza viwavi.",
        "Sur jeune maïs, ramassez à la main les pontes et les larves ; du sable sec, de la terre ou de la cendre déposés dans le cornet peuvent aussi réduire les larves."),
    "ROGUE": (
        "Remove infected plants as soon as symptoms appear, and replace them with healthy plants where practical.",
        "Ondoa mimea iliyoambukizwa mara dalili zinapoonekana, na ibadilishe kwa mimea yenye afya inapowezekana.",
        "Arrachez les plants infectés dès l'apparition des symptômes et remplacez-les par des plants sains si possible."),

    # ---- farm practices (this season) ----------------------------------
    "AVOID_WET_WORK": (
        "Avoid overhead irrigation and do not work in the crop while leaves are wet; water at the base in the morning.",
        "Epuka umwagiliaji wa juu ya majani na usifanye kazi shambani majani yakiwa na unyevu; mwagilia chini ya mmea asubuhi.",
        "Évitez l'irrigation par aspersion et ne travaillez pas dans la culture quand les feuilles sont mouillées ; arrosez au pied, le matin."),
    "AIRFLOW": (
        "Improve air flow: use the recommended spacing, stake or trellis plants, prune lower leaves and keep weeds down.",
        "Boresha mzunguko wa hewa: tumia nafasi inayopendekezwa, weka vigingi au tegemezo, pogoa majani ya chini na dhibiti magugu.",
        "Améliorez la circulation de l'air : respectez l'écartement recommandé, tuteurez, taillez les feuilles basses et maîtrisez les mauvaises herbes."),
    "MULCH": (
        "Mulch around plants to reduce soil splash, which carries spores and bacteria onto leaves.",
        "Weka matandazo kuzunguka mimea ili kupunguza matone ya udongo yanayopeleka vimelea kwenye majani.",
        "Paillez autour des plants pour limiter les éclaboussures de terre qui projettent spores et bactéries sur les feuilles."),
    "BALANCED_FERT": (
        "Feed plants with balanced fertiliser; too much nitrogen makes many crops more susceptible (add potassium on low-potassium soils).",
        "Tumia mbolea iliyosawazishwa; naitrojeni nyingi huifanya mimea mingi iwe rahisi kuambukizwa (ongeza potasiamu kwenye udongo wenye upungufu).",
        "Apportez un engrais équilibré ; trop d'azote rend beaucoup de cultures plus sensibles (ajoutez de la potasse sur les sols pauvres)."),
    "DRAINAGE": (
        "Improve drainage and avoid waterlogging; plant on ridges or raised beds where soils stay wet.",
        "Boresha mifereji ya maji na epuka maji kutuama; panda kwenye matuta pale ardhi inapokaa na unyevu.",
        "Améliorez le drainage et évitez l'engorgement ; plantez sur billons ou planches surélevées là où le sol reste humide."),
    "WATER_STRESS": (
        "Water regularly and avoid drought stress; keep dust off the crop.",
        "Mwagilia mara kwa mara na epuka ukame; zuia vumbi kwenye mazao.",
        "Arrosez régulièrement et évitez le stress hydrique ; limitez la poussière sur la culture."),
    "WATER_NO_FLOW": (
        "Do not let irrigation or run-off water flow from affected plots into healthy ones, and avoid irrigating with water from streams that cross affected fields.",
        "Usiruhusu maji ya umwagiliaji au mafuriko kutiririka kutoka sehemu zilizoathirika kwenda zenye afya, na epuka kumwagilia kwa maji ya mito yanayopita kwenye mashamba yaliyoathirika.",
        "Ne laissez pas l'eau d'irrigation ou de ruissellement passer des parcelles atteintes aux parcelles saines, et n'irriguez pas avec l'eau de cours d'eau traversant des champs atteints."),
    "NO_WOUND": (
        "Avoid wounding roots and stems when weeding or cultivating; wounds let bacteria in.",
        "Epuka kujeruhi mizizi na mashina wakati wa kupalilia au kulima; vidonda huruhusu bakteria kuingia.",
        "Évitez de blesser racines et tiges lors du désherbage ou du binage ; les blessures laissent entrer les bactéries."),
    "HOLD_NITROGEN": (
        "Stop applying nitrogen fertiliser until the outbreak slows down.",
        "Acha kuweka mbolea ya naitrojeni hadi mlipuko utakapopungua.",
        "Suspendez les apports d'azote jusqu'à ce que l'épidémie ralentisse."),
    "PRUNE_SHADE": (
        "Prune and regulate shade so air moves freely and the canopy dries quickly.",
        "Pogoa na dhibiti kivuli ili hewa izunguke na majani yakauke haraka.",
        "Taillez et régulez l'ombrage pour que l'air circule et que le feuillage sèche vite."),
    "DELEAF": (
        "Cut off leaves with spots or streaks and remove the cut material from the plantation.",
        "Kata majani yenye madoa au michirizi na uyatoe nje ya shamba la migomba.",
        "Coupez les feuilles tachetées ou striées et évacuez-les de la bananeraie."),
    "DEBUD": (
        "Remove the male bud (ua la kiume) with a forked stick soon after the last hand of fruit forms, so insects cannot spread the bacteria.",
        "Ondoa ua la kiume (male bud) kwa kijiti chenye uma mara baada ya chane la mwisho kuundwa, ili wadudu wasieneze bakteria.",
        "Retirez le bourgeon mâle avec un bâton fourchu peu après la formation de la dernière main de bananes, pour que les insectes ne transmettent pas la bactérie."),
    "HARVEST_HYGIENE": (
        "Harvest regularly; pick up and destroy infected, fallen or mummified fruits and pods.",
        "Vuna mara kwa mara; okota na uharibu matunda au maganda yaliyoathirika, yaliyoanguka au yaliyokauka.",
        "Récoltez régulièrement ; ramassez et détruisez les fruits ou cabosses infectés, tombés ou momifiés."),
    "SHORT_PLUCK": (
        "Pluck at shorter intervals in wet weather so infected young shoots are removed before they release spores.",
        "Vuna majani kwa vipindi vifupi wakati wa mvua ili machipukizi machanga yaliyoambukizwa yaondolewe kabla ya kutoa vimelea.",
        "Cueillez à intervalles plus courts par temps humide pour retirer les jeunes pousses infectées avant qu'elles ne libèrent des spores."),
    "HARVEST_EARLY": (
        "Harvest earlier than usual: root damage gets worse the longer roots stay in the ground.",
        "Vuna mapema kuliko kawaida: uharibifu wa mizizi huongezeka kadri mizizi inavyokaa ardhini.",
        "Récoltez plus tôt que d'habitude : les dégâts sur les racines augmentent plus elles restent en terre."),
    "HAULM_KILL": (
        "If potato tops are heavily blighted, cut and remove them, then wait about 2 weeks before lifting tubers so the skins set and tubers are not infected at harvest.",
        "Kama majani ya viazi yameathirika sana, yakate na uyaondoe, kisha subiri takriban wiki 2 kabla ya kuvuna ili ngozi ya viazi ikomae na viazi visiambukizwe wakati wa kuvuna.",
        "Si les fanes de pomme de terre sont très atteintes, coupez-les et évacuez-les, puis attendez environ 2 semaines avant l'arrachage pour que la peau des tubercules durcisse et qu'ils ne soient pas contaminés à la récolte."),
    "CULL_PILES": (
        "Destroy volunteer potatoes and cull piles; they carry the disease from one season to the next.",
        "Haribu viazi vilivyoota vyenyewe na marundo ya viazi vilivyotupwa; hubeba ugonjwa kutoka msimu mmoja hadi mwingine.",
        "Détruisez les repousses de pomme de terre et les tas de déchets ; ils transmettent la maladie d'une saison à l'autre."),
    "DENSE_SPACING": (
        "Use the recommended close spacing so the canopy closes quickly; aphids land less on dense stands.",
        "Tumia nafasi ya karibu inayopendekezwa ili majani yafunike ardhi haraka; vidukari hutua kidogo kwenye shamba lenye mimea mingi.",
        "Utilisez l'écartement serré recommandé pour que le couvert se ferme vite ; les pucerons se posent moins sur les peuplements denses."),

    # ---- prevention (next season) --------------------------------------
    "ROTATE": (
        "Rotate with crops from a different plant family for at least 2-3 seasons before planting this crop in the same field.",
        "Panda mazao ya familia tofauti kwa angalau misimu 2-3 kabla ya kupanda zao hili tena kwenye shamba hilo.",
        "Pratiquez une rotation avec des cultures d'une autre famille pendant au moins 2 à 3 saisons avant de replanter cette culture au même endroit."),
    "ROTATE_LONG": (
        "Rotate with cereals or other non-host crops for 3-4 years; avoid tomato, potato, pepper, eggplant and tobacco in the same soil.",
        "Panda nafaka au mazao mengine yasiyoshambuliwa kwa miaka 3-4; epuka nyanya, viazi, pilipili, biringanya na tumbaku kwenye udongo huo.",
        "Pratiquez une rotation de 3 à 4 ans avec des céréales ou d'autres cultures non hôtes ; évitez tomate, pomme de terre, piment, aubergine et tabac sur le même sol."),
    "ROTATE_NONCEREAL": (
        "Rotate with a non-cereal crop (beans, potatoes, vegetables) for at least one season, and never plant maize after maize.",
        "Panda zao lisilo la nafaka (maharagwe, viazi, mboga) kwa angalau msimu mmoja, na usipande mahindi baada ya mahindi.",
        "Alternez avec une culture non céréalière (haricot, pomme de terre, légumes) pendant au moins une saison, et ne replantez jamais du maïs après du maïs."),
    "CLEAN_SEED": (
        "Use certified, disease-free seed or planting material; never keep seed from affected plants.",
        "Tumia mbegu au vipandikizi vilivyothibitishwa visivyo na ugonjwa; usiweke mbegu kutoka kwa mimea iliyoathirika.",
        "Utilisez des semences ou du matériel végétal certifiés et sains ; ne conservez jamais de semences issues de plants atteints."),
    "CLEAN_CUTTINGS": (
        "Take cuttings or suckers only from symptom-free mother plants and do not move planting material out of affected areas.",
        "Chukua vipandikizi au machipukizi kutoka kwa mimea mama isiyo na dalili pekee na usihamishe vipandikizi kutoka maeneo yaliyoathirika.",
        "Prélevez boutures ou rejets uniquement sur des plants mères sans symptômes et ne déplacez pas de matériel végétal hors des zones touchées."),
    "RESISTANT": (
        "Next season, plant resistant or tolerant varieties recommended by your national research institute or extension officer.",
        "Msimu ujao, panda aina sugu au zinazovumilia ugonjwa zinazopendekezwa na taasisi ya utafiti ya nchi yako au afisa ugani.",
        "À la prochaine saison, plantez des variétés résistantes ou tolérantes recommandées par votre institut de recherche ou votre conseiller agricole."),
    "RESISTANT_COFFEE": (
        "Replant or interplant with improved varieties resistant to leaf rust and berry disease from your coffee research institute (in Kenya, e.g. Ruiru 11 and Batian).",
        "Panda upya au changanya na aina zilizoboreshwa zinazostahimili kutu ya majani na ugonjwa wa matunda kutoka taasisi ya utafiti ya kahawa (Kenya, mf. Ruiru 11 na Batian).",
        "Replantez ou complétez avec des variétés améliorées résistantes à la rouille et à l'anthracnose des baies, proposées par votre institut de recherche caféière (au Kenya, ex. Ruiru 11 et Batian)."),
    "RESIDUE": (
        "After harvest, plough under or remove and destroy crop residues so the pathogen cannot carry over to the next crop.",
        "Baada ya mavuno, lima kuzika au ondoa na uharibu masalia ya mazao ili kisababishi cha ugonjwa kisiendelee msimu ujao.",
        "Après la récolte, enfouissez par labour ou retirez et détruisez les résidus de culture pour que l'agent pathogène ne passe pas à la culture suivante."),
    "PLANT_EARLY": (
        "Plant early in the season and avoid planting next to older, infected fields.",
        "Panda mapema msimu unapoanza na epuka kupanda karibu na mashamba ya zamani yenye ugonjwa.",
        "Semez tôt en saison et évitez de planter à côté de champs plus anciens déjà infectés."),
    "HOT_WATER_SEED": (
        "If certified seed is not available, treat brassica seed in hot water (50 °C for 20-30 minutes) before sowing.",
        "Kama mbegu zilizothibitishwa hazipatikani, tibu mbegu za kabichi/kale kwa maji moto (50 °C kwa dakika 20-30) kabla ya kupanda.",
        "Si des semences certifiées ne sont pas disponibles, traitez les semences de crucifères à l'eau chaude (50 °C pendant 20 à 30 minutes) avant le semis."),
    "NURSERY_NET": (
        "Raise seedlings under fine insect-proof netting and transplant only clean, vigorous seedlings.",
        "Kuza miche chini ya wavu mwembamba unaozuia wadudu na hamisha miche safi na yenye nguvu pekee.",
        "Élevez les plants sous un filet anti-insectes à mailles fines et ne repiquez que des plants sains et vigoureux."),
    "CSSV_OFFICIAL": (
        "Have infected trees confirmed and removed ('cutting out') through the cocoa authority's or extension service's programme, and replant with tolerant varieties.",
        "Thibitisha miti iliyoambukizwa na uiondoe ('cutting out') kupitia mpango wa mamlaka ya kakao au huduma ya ugani, kisha panda upya aina zinazostahimili.",
        "Faites confirmer et éliminer les arbres infectés (« cutting out ») via le programme de l'autorité cacaoyère ou du service de vulgarisation, puis replantez avec des variétés tolérantes."),

    # ---- biological / low-cost -----------------------------------------
    "BIO_NEEM": (
        "Neem-based products help against aphids, mites and young caterpillars; spray in the evening and repeat as the label says.",
        "Bidhaa za mwarobaini husaidia dhidi ya vidukari, utitiri na viwavi wachanga; nyunyizia jioni na urudie kama maelekezo yanavyosema.",
        "Les produits à base de neem aident contre pucerons, acariens et jeunes chenilles ; pulvérisez le soir et répétez selon l'étiquette."),
    "BIO_BT": (
        "Bacillus thuringiensis (Bt) products control caterpillars and spare most beneficial insects; spray when larvae are small.",
        "Bidhaa za Bacillus thuringiensis (Bt) hudhibiti viwavi bila kudhuru wadudu wengi wasaidizi; nyunyizia viwavi wakiwa wadogo.",
        "Les produits à base de Bacillus thuringiensis (Bt) contrôlent les chenilles tout en épargnant la plupart des auxiliaires ; traitez quand les larves sont petites."),
    "BIO_TRICHO": (
        "Biological fungicides (Trichoderma or Bacillus subtilis products) can reduce fungal disease when used early and as prevention.",
        "Dawa za kibaiolojia za kuua kuvu (Trichoderma au Bacillus subtilis) zinaweza kupunguza magonjwa ya kuvu zikitumika mapema kama kinga.",
        "Les biofongicides (produits à base de Trichoderma ou Bacillus subtilis) peuvent réduire les maladies fongiques s'ils sont utilisés tôt et en préventif."),
    "BIO_ENEMIES": (
        "Protect natural enemies (insects that feed on or parasitise pests, such as ladybirds, parasitic wasps and predatory mites): avoid broad-spectrum sprays.",
        "Linda wadudu wasaidizi (wanaowinda au kuua wadudu waharibifu, kama ladybirds, nyigu wadogo na utitiri wawindaji): epuka dawa zinazoua kila aina ya wadudu.",
        "Protégez les auxiliaires (insectes qui se nourrissent des ravageurs ou les parasitent : coccinelles, guêpes parasitoïdes, acariens prédateurs) : évitez les produits à large spectre."),
    "BIO_SOAP": (
        "A strong water spray or insecticidal soap reduces mites, aphids and whiteflies; repeat every 5-7 days.",
        "Kunyunyizia maji kwa nguvu au sabuni ya kuua wadudu hupunguza utitiri, vidukari na inzi weupe; rudia kila siku 5-7.",
        "Un jet d'eau puissant ou un savon insecticide réduit acariens, pucerons et aleurodes ; répétez tous les 5 à 7 jours."),
    "PUSHPULL": (
        "Intercrop maize with desmodium and plant Napier grass borders (push-pull) to reduce stem borers and fall armyworm.",
        "Panda desmodium kati ya mahindi na nyasi ya Napier pembeni (push-pull) ili kupunguza vipekecha shina na viwavi jeshi vamizi.",
        "Associez le maïs au desmodium et plantez une bordure d'herbe à éléphant (push-pull) pour réduire foreurs de tiges et chenille légionnaire d'automne."),
    "TRAPS": (
        "Set pheromone traps to monitor and reduce adult moths.",
        "Weka mitego ya pheromone kufuatilia na kupunguza nondo wakubwa.",
        "Installez des pièges à phéromones pour surveiller et réduire les papillons adultes."),

    # ---- chemical (always: registered product, label rate, PPE) ---------
    "CHEM_COPPER": (
        "Copper-based fungicide/bactericide (e.g. copper oxychloride or copper hydroxide) as a protective spray; it slows spread but cannot repair damaged tissue.",
        "Dawa ya shaba (copper oxychloride au copper hydroxide) kama kinga; hupunguza kuenea lakini haiponyi tishu zilizoharibika.",
        "Fongicide/bactéricide cuivrique (ex. oxychlorure ou hydroxyde de cuivre) en protection ; il ralentit la propagation mais ne répare pas les tissus abîmés."),
    "CHEM_PROTECTANT": (
        "Protectant fungicide such as mancozeb (or chlorothalonil where registered), applied at the first symptoms and repeated at label intervals in wet weather.",
        "Dawa ya kinga ya kuua kuvu kama mancozeb (au chlorothalonil pale iliposajiliwa), ipakwe dalili za kwanza zinapoonekana na kurudiwa kwa vipindi vya lebo wakati wa mvua.",
        "Fongicide de contact comme le mancozèbe (ou le chlorothalonil là où il est homologué), dès les premiers symptômes et renouvelé selon l'étiquette par temps humide."),
    "CHEM_LATE_BLIGHT": (
        "Alternate a protectant (mancozeb) with a systemic or translaminar product (e.g. mixtures with metalaxyl-M, cymoxanil, dimethomorph or fluopicolide); never repeat the same mode of action.",
        "Badilisha dawa ya kinga (mancozeb) na dawa inayoingia ndani ya mmea (mf. mchanganyiko wenye metalaxyl-M, cymoxanil, dimethomorph au fluopicolide); usirudie kundi lile lile la dawa.",
        "Alternez un produit de contact (mancozèbe) avec un produit systémique ou translaminaire (ex. mélanges à base de métalaxyl-M, cymoxanil, diméthomorphe ou fluopicolide) ; ne répétez jamais le même mode d'action."),
    "CHEM_SYSTEMIC": (
        "Systemic fungicide from the triazole (e.g. propiconazole, tebuconazole) or strobilurin (e.g. azoxystrobin) groups only when needed, rotating groups to avoid resistance.",
        "Dawa inayoingia ndani ya mmea ya kundi la triazole (mf. propiconazole, tebuconazole) au strobilurin (mf. azoxystrobin) tu inapohitajika, ukibadilisha makundi ili kuepuka usugu.",
        "Fongicide systémique des groupes triazoles (ex. propiconazole, tébuconazole) ou strobilurines (ex. azoxystrobine), seulement si nécessaire, en alternant les groupes pour éviter les résistances."),
    "CHEM_SULPHUR": (
        "Wettable sulphur or potassium bicarbonate against powdery mildew; avoid hot weather (above about 30 °C), when sulphur can scorch leaves.",
        "Salfa inayoyeyuka (wettable sulphur) au potassium bicarbonate dhidi ya ukungu wa unga; epuka joto kali (juu ya takriban 30 °C) kwani salfa inaweza kuunguza majani.",
        "Soufre mouillable ou bicarbonate de potassium contre l'oïdium ; évitez les fortes chaleurs (au-dessus de 30 °C environ) où le soufre peut brûler les feuilles."),
    "CHEM_CATERPILLAR": (
        "Insecticide registered for caterpillars on this crop (e.g. emamectin benzoate, spinetoram or chlorantraniliprole), sprayed in the evening or early morning; rotate modes of action.",
        "Dawa ya wadudu iliyosajiliwa kwa viwavi kwenye zao hili (mf. emamectin benzoate, spinetoram au chlorantraniliprole), inyunyizwe jioni au asubuhi mapema; badilisha makundi ya dawa.",
        "Insecticide homologué contre les chenilles sur cette culture (ex. émamectine benzoate, spinétoram ou chlorantraniliprole), appliqué le soir ou tôt le matin ; alternez les modes d'action."),
    "CHEM_VECTOR": (
        "Use an insecticide registered for the insect that spreads this disease (whitefly, aphid, thrips or leafhopper) only where it is present, and rotate modes of action.",
        "Tumia dawa ya wadudu iliyosajiliwa kwa mdudu anayeeneza ugonjwa huu (inzi mweupe, vidukari, thrips au leafhoppers) pale tu anapoonekana, na badilisha makundi ya dawa.",
        "Utilisez un insecticide homologué contre l'insecte vecteur (aleurode, puceron, thrips ou cicadelle), seulement là où il est présent, en alternant les modes d'action."),
    "CHEM_MITE": (
        "Miticide registered for the crop (e.g. abamectin or spiromesifen) only if mites are numerous; avoid pyrethroids, which can make mite outbreaks worse.",
        "Dawa ya kuua utitiri iliyosajiliwa kwa zao hili (mf. abamectin au spiromesifen) tu utitiri wakiwa wengi; epuka pyrethroids kwani zinaweza kuzidisha utitiri.",
        "Acaricide homologué sur la culture (ex. abamectine ou spiromésifène) seulement si les acariens sont nombreux ; évitez les pyréthrinoïdes qui peuvent aggraver les pullulations."),
    "CHEM_AVOID_MITE_ENEMIES": (
        "Avoid routine spraying: it kills the predatory mites that normally keep this pest under control.",
        "Epuka kunyunyizia mara kwa mara: huua utitiri wawindaji ambao kwa kawaida hudhibiti mdudu huyu.",
        "Évitez les traitements systématiques : ils tuent les acariens prédateurs qui régulent normalement ce ravageur."),
    "CHEM_NONE": (
        "No chemical cures this problem; spraying will not save infected plants. Focus on removal, hygiene and prevention.",
        "Hakuna dawa ya kemikali inayoponya tatizo hili; kunyunyizia hakutaokoa mimea iliyoambukizwa. Zingatia kuondoa, usafi na kinga.",
        "Aucun produit chimique ne guérit ce problème ; pulvériser ne sauvera pas les plants infectés. Misez sur l'élimination, l'hygiène et la prévention."),
    "CHEM_RICE": (
        "Blast fungicide (e.g. tricyclazole or azoxystrobin-based) at the crop stage and rate on the label if the disease is severe.",
        "Dawa ya kuua kuvu ya blast (mf. yenye tricyclazole au azoxystrobin) kwa hatua ya zao na kiwango kilichoelekezwa kwenye lebo ikiwa ugonjwa ni mkali.",
        "Fongicide anti-pyriculariose (ex. à base de tricyclazole ou d'azoxystrobine) au stade et à la dose de l'étiquette si l'attaque est sévère."),
    "CHEM_COFFEE": (
        "Follow your local coffee spray programme: preventive copper sprays, with systemic triazole mixtures where your extension officer advises.",
        "Fuata ratiba ya dawa ya kahawa ya eneo lako: dawa ya shaba kama kinga, pamoja na mchanganyiko wa triazole pale afisa ugani anaposhauri.",
        "Suivez le programme de traitement caféier de votre région : cuivre en préventif, avec des mélanges systémiques à base de triazoles si votre conseiller agricole le recommande."),
    "CHEM_POD": (
        "Copper-based fungicide (e.g. cuprous oxide or copper hydroxide), or a metalaxyl-copper mix, per your national cocoa programme; cover the pods well.",
        "Dawa ya shaba (mf. cuprous oxide au copper hydroxide), au mchanganyiko wa metalaxyl na shaba, kulingana na mpango wa kitaifa wa kakao; nyunyizia maganda vizuri.",
        "Fongicide cuivrique (ex. oxyde cuivreux ou hydroxyde de cuivre), ou mélange métalaxyl-cuivre, selon le programme national cacao ; couvrez bien les cabosses."),
    "SPRAY_WINDOW": (
        "On susceptible varieties, spray only when lesions reach the upper leaves before or around tasselling; later sprays rarely pay.",
        "Kwa aina zinazoshambuliwa kwa urahisi, nyunyizia tu madoa yanapofika majani ya juu kabla au wakati wa kutoa mashada; kunyunyizia baadaye mara chache huwa na faida.",
        "Sur variétés sensibles, ne traitez que lorsque les lésions atteignent les feuilles supérieures avant ou autour de l'émission des panicules ; les traitements tardifs sont rarement rentables."),
    "SPRAY_RUST": (
        "On susceptible wheat, spray a triazole or strobilurin fungicide promptly when rust first appears and repeat at label intervals if wet weather continues; rust spreads very fast.",
        "Kwa ngano inayoshambuliwa kwa urahisi, nyunyizia dawa ya triazole au strobilurin mara kutu inapoanza kuonekana na urudie kwa vipindi vya lebo mvua ikiendelea; kutu huenea haraka sana.",
        "Sur blé sensible, traitez rapidement avec un fongicide triazole ou strobilurine dès l'apparition de la rouille et renouvelez selon l'étiquette si le temps reste humide ; la rouille se propage très vite."),
    "FAW_TIMING": (
        "Spray early, when larvae are small and in the whorl; once they are inside the cob, sprays work poorly.",
        "Nyunyizia mapema viwavi wakiwa wadogo na wako kwenye shina la majani (whorl); wakishaingia kwenye gunzi, dawa hufanya kazi hafifu.",
        "Traitez tôt, quand les larves sont petites et dans le cornet ; une fois dans l'épi, les traitements sont peu efficaces."),
}

# ----------------------------------------------------------------------------
# Diseases
# ----------------------------------------------------------------------------
DISEASES = {}


def _d(key, kind, crops, nm, sg, now=(), cult=(), bio=(), chem=(), prev=(),
       severe=(), report=False, epi=None, alias=(), extra=None):
    """Register a disease.  nm / sg are (en, sw, fr) tuples."""
    DISEASES[key] = {
        "kind": kind,                 # fungal | bacterial | viral | pest | healthy
        "crops": list(crops),         # crop families (empty = any)
        "name": nm,
        "signs": sg,
        "now": list(now), "cult": list(cult), "bio": list(bio),
        "chem": list(chem), "prev": list(prev), "severe": list(severe),
        "report": report,
        "epi": epi or nm[0],          # canonical English label used in surveillance statistics
        "alias": list(alias),
        "extra": extra or {},         # {family: {section: [codes]}}
    }


_d("healthy", "healthy", [],
   ("Healthy", "Mmea wenye afya (Healthy)", "Sain"),
   ("The leaf looks normal: even green colour, no spots, streaks, mould or insect damage.",
    "Jani linaonekana kawaida: rangi ya kijani sawa, hakuna madoa, michirizi, ukungu wala uharibifu wa wadudu.",
    "La feuille paraît normale : couleur verte uniforme, sans taches, stries, moisissure ni dégâts d'insectes."),
   now=["SCOUT"],
   prev=["AIRFLOW", "BALANCED_FERT", "MULCH", "CLEAN_SEED", "ROTATE"],
   alias=["healthy", "afya", "sain"])

# ---- Tomato / potato ----------------------------------------------------
_d("late_blight", "fungal", ["tomato", "potato"],
   ("Late Blight", "Ukungu wa Viazi na Nyanya (Late Blight)", "Mildiou (Phytophthora infestans)"),
   ("Water-soaked grey-green patches that turn brown-black on leaves and stems, often with white fuzzy growth underneath in humid weather; fruit and tubers get firm brown rot.",
    "Mabaka yenye maji ya kijani-kijivu yanayogeuka kahawia-nyeusi kwenye majani na mashina, mara nyingi na ukungu mweupe chini ya jani wakati wa unyevu; matunda na viazi huoza kahawia na kuwa vigumu.",
    "Taches grises-vertes d'aspect huileux qui brunissent puis noircissent sur feuilles et tiges, souvent avec un duvet blanc dessous par temps humide ; fruits et tubercules pourrissent (pourriture brune ferme)."),
   now=["REMOVE_LEAVES", "ISOLATE", "SCOUT"],
   cult=["AVOID_WET_WORK", "AIRFLOW"],
   chem=["CHEM_LATE_BLIGHT", "CHEM_COPPER"],
   prev=["CLEAN_SEED", "RESISTANT", "ROTATE", "DRAINAGE"],
   severe=["UPROOT_DESTROY"],
   alias=["late blight", "blight", "ukungu wa viazi", "ukungu", "mildiou", "phytophthora"],
   extra={"potato": {"cult": ["HAULM_KILL"], "prev": ["CULL_PILES"]}})

_d("early_blight", "fungal", ["tomato", "potato"],
   ("Early Blight", "Ukungu wa Mapema (Early Blight)", "Alternariose (Alternaria solani)"),
   ("Brown spots with ring-like (target) patterns and a yellow halo, starting on the oldest, lowest leaves; stems and fruit can also be affected.",
    "Madoa ya kahawia yenye pete-pete (kama shabaha) na mduara wa njano, yakianza kwenye majani ya zamani ya chini; mashina na matunda pia yanaweza kuathirika.",
    "Taches brunes à anneaux concentriques (en cible) avec un halo jaune, qui débutent sur les plus vieilles feuilles basses ; tiges et fruits peuvent aussi être touchés."),
   now=["REMOVE_LEAVES", "ISOLATE"],
   cult=["MULCH", "AVOID_WET_WORK", "BALANCED_FERT"],
   bio=["BIO_TRICHO"],
   chem=["CHEM_PROTECTANT", "CHEM_SYSTEMIC", "CHEM_COPPER"],
   prev=["ROTATE", "RESIDUE", "RESISTANT", "CLEAN_SEED"],
   alias=["early blight", "alternaria", "alternariose", "ukungu wa mapema"],
   extra={"potato": {"prev": ["CULL_PILES"]}})

_d("septoria_leaf_spot", "fungal", ["tomato"],
   ("Septoria Leaf Spot", "Madoa ya Septoria (Septoria Leaf Spot)", "Septoriose"),
   ("Many small round spots with grey-white centres and dark edges, mostly on lower leaves, with tiny black dots in the centre; leaves yellow and drop.",
    "Madoa mengi madogo ya duara yenye kituo cha kijivu-nyeupe na kingo nyeusi, hasa kwenye majani ya chini, yenye vitone vidogo vyeusi katikati; majani hugeuka njano na kudondoka.",
    "Nombreuses petites taches rondes au centre gris-blanc et au bord sombre, surtout sur les feuilles basses, avec de minuscules points noirs au centre ; les feuilles jaunissent et tombent."),
   now=["REMOVE_LEAVES", "ISOLATE"],
   cult=["MULCH", "AVOID_WET_WORK", "AIRFLOW"],
   bio=["BIO_TRICHO"],
   chem=["CHEM_PROTECTANT", "CHEM_COPPER"],
   prev=["ROTATE", "RESIDUE", "CLEAN_SEED", "CLEAR_WEEDS"],
   alias=["septoria", "septoriose"])

_d("bacterial_spot", "bacterial", ["tomato"],
   ("Bacterial Spot", "Madoa ya Bakteria (Bacterial Spot)", "Tache bactérienne"),
   ("Small dark, greasy-looking spots on leaves (often with a yellow halo) and rough, scabby spots on fruit; spreads in warm, wet, windy weather.",
    "Madoa madogo meusi yanayoonekana kuwa na mafuta kwenye majani (mara nyingi na mduara wa njano) na madoa magumu yenye magamba kwenye matunda; huenea hali ya joto, mvua na upepo.",
    "Petites taches sombres d'aspect gras sur les feuilles (souvent avec halo jaune) et taches rugueuses et croûteuses sur les fruits ; se propage par temps chaud, humide et venteux."),
   now=["REMOVE_LEAVES", "ISOLATE", "DISINFECT_TOOLS"],
   cult=["AVOID_WET_WORK", "MULCH", "AIRFLOW"],
   chem=["CHEM_COPPER"],
   prev=["CLEAN_SEED", "ROTATE", "RESIDUE"],
   alias=["bacterial spot", "bacterial speck", "tache bactérienne", "madoa ya bakteria"])

_d("leaf_mold", "fungal", ["tomato"],
   ("Leaf Mold", "Ukungu wa Majani ya Nyanya (Leaf Mold)", "Cladosporiose (moisissure des feuilles)"),
   ("Pale green-yellow patches on the upper leaf surface with olive-brown velvety mould underneath; common in humid, poorly ventilated tomatoes (especially in greenhouses).",
    "Mabaka ya kijani-njano hafifu juu ya jani na ukungu wa kahawia-mzeituni unaofanana na kitambaa chini ya jani; hutokea sana kwenye nyanya zenye unyevu na hewa duni (hasa kwenye greenhouse).",
    "Plages vert pâle-jaunes sur la face supérieure avec un feutrage brun-olive dessous ; fréquent sur tomates en milieu humide et mal aéré (surtout sous serre)."),
   now=["REMOVE_LEAVES"],
   cult=["AIRFLOW", "AVOID_WET_WORK"],
   chem=["CHEM_PROTECTANT", "CHEM_COPPER"],
   prev=["RESISTANT", "CLEAN_SEED", "RESIDUE"],
   alias=["leaf mold", "leaf mould", "cladosporiose"])

_d("target_spot", "fungal", ["tomato"],
   ("Target Spot", "Madoa ya Duara (Target Spot)", "Maladie des taches cibles (Corynespora)"),
   ("Brown spots with concentric rings and a yellow border on leaves, stems and fruit; looks like early blight but is common in hot, humid weather.",
    "Madoa ya kahawia yenye pete za duara na ukingo wa njano kwenye majani, mashina na matunda; hufanana na early blight lakini hutokea sana kwenye joto na unyevu.",
    "Taches brunes à anneaux concentriques et bordure jaune sur feuilles, tiges et fruits ; ressemble à l'alternariose mais fréquente par temps chaud et humide."),
   now=["REMOVE_LEAVES"],
   cult=["AIRFLOW", "MULCH", "AVOID_WET_WORK"],
   chem=["CHEM_PROTECTANT", "CHEM_SYSTEMIC"],
   prev=["ROTATE", "RESIDUE", "CLEAN_SEED"],
   alias=["target spot", "corynespora"])

_d("tomato_leaf_curl_virus", "viral", ["tomato"],
   ("Tomato Yellow Leaf Curl Virus", "Virusi vya Kujikunja Majani ya Nyanya (Tomato Leaf Curl Virus)", "Virus de l'enroulement jaune en cuillère (TYLCV)"),
   ("Leaves curl upwards, become small, thick and yellow at the edges; plants stay stunted with few fruits; whiteflies are usually present.",
    "Majani hujikunja kwenda juu, huwa madogo, mazito na ya njano pembeni; mimea hudumaa na kuzaa matunda machache; inzi weupe huwepo mara nyingi.",
    "Feuilles enroulées vers le haut, petites, épaisses et jaunes sur les bords ; plants nanifiés avec peu de fruits ; aleurodes généralement présents."),
   now=["ROGUE", "SCOUT"],
   cult=["CLEAR_WEEDS"],
   bio=["BIO_SOAP", "BIO_ENEMIES"],
   chem=["CHEM_NONE", "CHEM_VECTOR"],
   prev=["RESISTANT", "NURSERY_NET", "CLEAN_SEED"],
   epi="Leaf Curl Virus",
   alias=["leaf curl", "curl virus", "tylcv", "kujikunja"])

_d("mosaic_virus", "viral", ["tomato", "cowpea", "beans", "nightshade", "spiderplant"],
   ("Mosaic Virus", "Virusi vya Mosaic (Mosaic Virus)", "Virus de la mosaïque"),
   ("Light and dark green mottling (mosaic) on leaves, distorted or fern-like leaves and stunted growth; spreads on hands and tools, by aphids or through seed.",
    "Rangi za kijani hafifu na nzito (mosaic) kwenye majani, majani yaliyopinda au kama feri na ukuaji uliodumaa; huenea kwa mikono na vifaa, vidukari au mbegu.",
    "Marbrures vert clair et vert foncé (mosaïque) sur les feuilles, feuilles déformées ou en fougère et croissance réduite ; se transmet par les mains, les outils, les pucerons ou la semence."),
   now=["ROGUE", "DISINFECT_TOOLS", "ISOLATE"],
   cult=["WASH_HANDS", "CLEAR_WEEDS"],
   chem=["CHEM_NONE", "CHEM_VECTOR"],
   prev=["CLEAN_SEED", "RESISTANT", "RESIDUE"],
   alias=["mosaic virus", "mosaic", "mosaïque", "mosaic ya"])

_d("spider_mites", "pest", ["tomato", "beans", "cowpea"],
   ("Spider Mites", "Utitiri Buibui (Spider Mites)", "Acariens (araignées rouges)"),
   ("Tiny yellow-white speckles on leaves, fine webbing underneath, leaves turn bronze and dry; worst in hot, dry, dusty weather.",
    "Vitone vidogo vya njano-nyeupe kwenye majani, utando mwembamba chini ya jani, majani hubadilika rangi ya shaba na kukauka; huwa mbaya zaidi kwenye joto, ukavu na vumbi.",
    "Minuscules ponctuations jaune-blanc sur les feuilles, fine toile dessous, feuilles bronzées puis desséchées ; pire par temps chaud, sec et poussiéreux."),
   now=["BIO_SOAP", "REMOVE_LEAVES"],
   cult=["WATER_STRESS", "CLEAR_WEEDS"],
   bio=["BIO_ENEMIES", "BIO_NEEM"],
   chem=["CHEM_MITE"],
   prev=["SCOUT"],
   alias=["spider mite", "mites", "utitiri", "acarien"])

_d("tuta_absoluta", "pest", ["tomato", "potato"],
   ("Tuta absoluta (tomato leaf miner)", "Nondo wa Nyanya (Tuta absoluta)", "Mineuse de la tomate (Tuta absoluta)"),
   ("Winding tunnels (mines) in leaves that look like blotches, holes bored into fruit and stems, black droppings; small caterpillars inside.",
    "Mitaro inayopinda (mines) kwenye majani inayoonekana kama mabaka, mashimo kwenye matunda na mashina, kinyesi cheusi; viwavi wadogo ndani.",
    "Galeries sinueuses (mines) dans les feuilles ressemblant à des plages desséchées, trous dans fruits et tiges, déjections noires ; petites chenilles à l'intérieur."),
   now=["REMOVE_LEAVES", "TRAPS"],
   cult=["CLEAR_WEEDS", "RESIDUE"],
   bio=["BIO_BT", "BIO_NEEM", "BIO_ENEMIES"],
   chem=["CHEM_CATERPILLAR"],
   prev=["NURSERY_NET", "ROTATE"],
   epi="Tuta Absoluta",
   alias=["tuta", "tuta absoluta", "leaf miner", "leafminer", "mineuse", "nondo wa nyanya"])

_d("bacterial_wilt", "bacterial", ["tomato", "potato"],
   ("Bacterial Wilt", "Mnyauko wa Bakteria (Bacterial Wilt)", "Flétrissement bactérien (Ralstonia)"),
   ("Sudden wilting of the whole plant while still green; a cut stem placed in clear water releases milky threads; potato tubers show a brown ring and sticky ooze.",
    "Mmea mzima hunyauka ghafla ukiwa bado kijani; shina lililokatwa likiwekwa kwenye maji safi hutoa nyuzi nyeupe-maziwa; viazi huonyesha duara la kahawia na utomvu unaonata.",
    "Flétrissement brusque de toute la plante encore verte ; une tige coupée placée dans l'eau claire libère des filets laiteux ; les tubercules montrent un anneau brun et un suintement collant."),
   now=["UPROOT_DESTROY", "DISINFECT_TOOLS", "RESTRICT_MOVEMENT", "REPORT"],
   cult=["WATER_NO_FLOW", "NO_WOUND"],
   chem=["CHEM_NONE"],
   prev=["ROTATE_LONG", "CLEAN_SEED", "RESISTANT", "DRAINAGE", "CLEAR_WEEDS"],
   report=True,
   alias=["bacterial wilt", "wilt", "mnyauko", "flétrissement", "ralstonia", "brown rot"])

# ---- Maize --------------------------------------------------------------
_d("northern_leaf_blight", "fungal", ["maize"],
   ("Northern Leaf Blight", "Ukungu wa Majani wa Kaskazini (Northern Leaf Blight)", "Helminthosporiose du maïs (brûlure foliaire du nord)"),
   ("Long, cigar-shaped grey-green to tan lesions (2.5-15 cm) on leaves, starting on lower leaves and moving upward in cool, humid weather.",
    "Madoa marefu yenye umbo la sigara ya kijani-kijivu hadi hudhurungi (sm 2.5-15) kwenye majani, yakianzia majani ya chini na kupanda juu wakati wa baridi na unyevu.",
    "Longues lésions en forme de cigare, gris-vert à beige (2,5-15 cm), débutant sur les feuilles basses et montant par temps frais et humide."),
   now=["SCOUT"],
   cult=["AIRFLOW", "CLEAR_WEEDS"],
   chem=["SPRAY_WINDOW", "CHEM_SYSTEMIC"],
   prev=["RESISTANT", "ROTATE", "RESIDUE", "PLANT_EARLY", "BALANCED_FERT"],
   alias=["northern leaf blight", "leaf blight", "turcicum", "helminthosporiose", "nlb"])

_d("gray_leaf_spot", "fungal", ["maize"],
   ("Gray Leaf Spot", "Madoa Kijivu ya Majani (Gray Leaf Spot)", "Cercosporiose du maïs (taches grises)"),
   ("Narrow, rectangular grey to tan lesions running parallel to the leaf veins; in humid weather they join up and kill whole leaves.",
    "Madoa membamba ya mstatili ya kijivu hadi hudhurungi yanayofuata mishipa ya jani; wakati wa unyevu huungana na kuua majani yote.",
    "Lésions étroites et rectangulaires gris à beige parallèles aux nervures ; par temps humide elles fusionnent et tuent des feuilles entières."),
   now=["SCOUT"],
   cult=["AIRFLOW", "CLEAR_WEEDS"],
   chem=["SPRAY_WINDOW", "CHEM_SYSTEMIC"],
   prev=["RESISTANT", "RESIDUE", "ROTATE", "PLANT_EARLY", "BALANCED_FERT"],
   alias=["gray leaf spot", "grey leaf spot", "cercospora", "cercosporiose", "gls"])

_d("common_rust", "fungal", ["maize"],
   ("Common Rust", "Kutu ya Mahindi (Common Rust)", "Rouille commune du maïs"),
   ("Small, round to oval, powdery brick-red to brown pustules on both sides of the leaf that burst open and release rusty spores.",
    "Vipele vidogo vya duara hadi mviringo vyenye unga wa rangi ya matofali-nyekundu hadi kahawia pande zote za jani, vinavyopasuka na kutoa vimelea vya kutu.",
    "Petites pustules rondes à ovales, poudreuses, rouge brique à brunes sur les deux faces de la feuille, qui éclatent et libèrent des spores rouille."),
   now=["SCOUT"],
   cult=["AIRFLOW"],
   chem=["SPRAY_WINDOW", "CHEM_SYSTEMIC"],
   prev=["RESISTANT", "PLANT_EARLY", "RESIDUE"],
   alias=["common rust", "rust", "kutu", "rouille"])

_d("maize_streak_virus", "viral", ["maize"],
   ("Maize Streak Virus", "Virusi vya Michirizi ya Mahindi (Maize Streak Virus)", "Virus de la striure du maïs (MSV)"),
   ("Narrow, broken yellow streaks along the veins of young leaves and stunted plants; spread by leafhoppers living on grasses.",
    "Michirizi myembamba ya njano iliyokatika kando ya mishipa ya majani machanga na mimea iliyodumaa; huenezwa na leafhoppers wanaoishi kwenye nyasi.",
    "Fines stries jaunes interrompues le long des nervures des jeunes feuilles et plants nanifiés ; transmis par des cicadelles vivant sur les graminées."),
   now=["ROGUE", "CLEAR_WEEDS"],
   chem=["CHEM_NONE", "CHEM_VECTOR"],
   prev=["RESISTANT", "PLANT_EARLY", "CLEAR_WEEDS"],
   alias=["maize streak", "streak virus", "streak", "msv", "striure"])

_d("maize_lethal_necrosis", "viral", ["maize"],
   ("Maize Lethal Necrosis", "Ugonjwa wa Kifo cha Mahindi (Maize Lethal Necrosis, MLN)", "Nécrose létale du maïs (MLN)"),
   ("Yellowing that starts at leaf edges and spreads to the midrib, leaves drying from the margins, young leaves dying ('dead heart'), and small deformed cobs with little grain.",
    "Kuwa njano kunakoanzia pembeni mwa jani na kuenea hadi mshipa wa kati, majani kukauka kutoka pembeni, majani machanga kufa ('dead heart'), na magunzi madogo yaliyoharibika yenye punje chache.",
    "Jaunissement débutant aux bords des feuilles et gagnant la nervure centrale, dessèchement des marges, mort des jeunes feuilles (« cœur mort ») et petits épis déformés avec peu de grains."),
   now=["UPROOT_DESTROY", "REPORT", "RESTRICT_MOVEMENT"],
   cult=["CLEAR_WEEDS"],
   chem=["CHEM_NONE", "CHEM_VECTOR"],
   prev=["CLEAN_SEED", "ROTATE_NONCEREAL", "RESISTANT", "CLEAR_WEEDS"],
   report=True,
   alias=["maize lethal necrosis", "lethal necrosis", "mln", "necrose letale", "nécrose létale"])

_d("fall_armyworm", "pest", ["maize", "rice", "wheat"],
   ("Fall Armyworm", "Viwavi Jeshi Vamizi (Fall Armyworm)", "Chenille légionnaire d'automne"),
   ("Ragged holes and 'window-pane' scraping in young leaves, sawdust-like droppings (frass) in the whorl; caterpillars have an inverted 'Y' on the head and four dark dots at the tail end.",
    "Mashimo yaliyokatika-katika na kukwaruzwa kama 'dirisha' kwenye majani machanga, kinyesi kama vumbi la mbao kwenye shina la majani (whorl); viwavi wana alama ya 'Y' iliyopinduliwa kichwani na vitone vinne vyeusi mkiani.",
    "Trous irréguliers et grattages en « fenêtres » sur les jeunes feuilles, déjections ressemblant à de la sciure dans le cornet ; les chenilles portent un « Y » inversé sur la tête et quatre points sombres à l'extrémité de l'abdomen."),
   now=["SAND_WHORL", "SCOUT"],
   cult=["CLEAR_WEEDS", "RESIDUE"],
   bio=["BIO_BT", "BIO_NEEM", "BIO_ENEMIES", "PUSHPULL"],
   chem=["CHEM_CATERPILLAR", "FAW_TIMING"],
   prev=["PLANT_EARLY", "TRAPS", "ROTATE"],
   alias=["fall armyworm", "armyworm", "army worm", "faw", "viwavi", "legionnaire", "légionnaire"])

# ---- Beans --------------------------------------------------------------
_d("angular_leaf_spot", "fungal", ["beans"],
   ("Angular Leaf Spot", "Madoa ya Pembe kwenye Majani (Angular Leaf Spot)", "Tache angulaire du haricot"),
   ("Angular grey-brown spots limited by the leaf veins that later dry and fall out, giving a ragged 'shot-hole' look; pods get dark spots.",
    "Madoa yenye pembe ya kijivu-kahawia yanayozuiwa na mishipa ya jani, baadaye hukauka na kudondoka na kuacha mashimo; maganda hupata madoa meusi.",
    "Taches anguleuses gris-brun limitées par les nervures, qui sèchent et tombent en laissant des trous ; les gousses portent des taches sombres."),
   now=["REMOVE_LEAVES", "ISOLATE"],
   cult=["AVOID_WET_WORK", "MULCH"],
   chem=["CHEM_PROTECTANT", "CHEM_COPPER"],
   prev=["CLEAN_SEED", "ROTATE", "RESIDUE", "RESISTANT"],
   alias=["angular leaf spot", "angular", "tache angulaire", "madoa ya pembe"])

_d("bean_rust", "fungal", ["beans"],
   ("Bean Rust", "Kutu ya Maharagwe (Bean Rust)", "Rouille du haricot"),
   ("Small reddish-brown powdery pustules, mostly under the leaf, often with a yellow halo; heavy attack dries the leaves and makes them fall.",
    "Vipele vidogo vya unga vya rangi ya kahawia-nyekundu, hasa chini ya jani, mara nyingi na mduara wa njano; shambulio kubwa hukausha majani na kuyaangusha.",
    "Petites pustules poudreuses brun-rouge, surtout sous la feuille, souvent avec un halo jaune ; une forte attaque dessèche et fait tomber les feuilles."),
   now=["SCOUT", "REMOVE_LEAVES"],
   cult=["AIRFLOW", "AVOID_WET_WORK"],
   chem=["CHEM_PROTECTANT", "CHEM_SYSTEMIC"],
   prev=["RESISTANT", "PLANT_EARLY", "ROTATE", "RESIDUE"],
   alias=["bean rust", "kutu ya maharagwe", "rouille du haricot"])

_d("anthracnose", "fungal", ["beans"],
   ("Anthracnose", "Anthracnose ya Maharagwe (madoa meusi yaliyozama)", "Anthracnose du haricot"),
   ("Dark, sunken brown-black lesions along leaf veins and on pods (with pinkish spore masses in wet weather); seedlings can show dark sunken stem spots.",
    "Madoa meusi-kahawia yaliyozama kando ya mishipa ya jani na kwenye maganda (yenye vimelea vya rangi ya waridi wakati wa mvua); miche inaweza kuwa na madoa meusi yaliyozama kwenye shina.",
    "Lésions brun-noir enfoncées le long des nervures et sur les gousses (avec masses de spores rosées par temps humide) ; les plantules peuvent présenter des taches sombres enfoncées sur la tige."),
   now=["REMOVE_LEAVES", "AVOID_WET_WORK", "ISOLATE"],
   chem=["CHEM_PROTECTANT", "CHEM_COPPER"],
   prev=["CLEAN_SEED", "ROTATE", "RESIDUE", "RESISTANT"],
   alias=["anthracnose", "anthracnose ya maharagwe"])

_d("common_bacterial_blight", "bacterial", ["beans"],
   ("Common Bacterial Blight", "Ukungu wa Bakteria wa Maharagwe (Common Bacterial Blight)", "Graisse commune (bactériose du haricot)"),
   ("Water-soaked spots that turn brown with a narrow yellow border and join into large dead patches; pods show greasy spots.",
    "Madoa yenye maji yanayogeuka kahawia na ukingo mwembamba wa njano na kuungana kuwa mabaka makubwa yaliyokufa; maganda huonyesha madoa yenye mafuta.",
    "Taches d'aspect huileux qui brunissent avec une fine bordure jaune et fusionnent en grandes plages mortes ; les gousses présentent des taches grasses."),
   now=["REMOVE_LEAVES", "ISOLATE", "AVOID_WET_WORK"],
   chem=["CHEM_COPPER"],
   prev=["CLEAN_SEED", "ROTATE", "RESIDUE", "RESISTANT"],
   alias=["common bacterial blight", "bacterial blight", "halo blight", "bactériose"])

# ---- Groundnut ----------------------------------------------------------
_d("early_leaf_spot", "fungal", ["groundnut"],
   ("Early Leaf Spot", "Madoa ya Mapema ya Majani (Early Leaf Spot)", "Cercosporiose précoce"),
   ("Dark brown spots with a yellow halo on the upper leaf surface, appearing about 4-6 weeks after planting; leaves yellow and drop.",
    "Madoa ya kahawia iliyokolea yenye mduara wa njano juu ya jani, yanayoonekana takriban wiki 4-6 baada ya kupanda; majani hugeuka njano na kudondoka.",
    "Taches brun foncé avec halo jaune sur la face supérieure, apparaissant 4 à 6 semaines environ après le semis ; les feuilles jaunissent et tombent."),
   now=["SCOUT"],
   cult=["AIRFLOW"],
   chem=["CHEM_PROTECTANT", "CHEM_SYSTEMIC"],
   prev=["RESISTANT", "ROTATE", "RESIDUE", "PLANT_EARLY", "CLEAN_SEED"],
   alias=["early leaf spot", "leaf spot", "tikka"])

_d("late_leaf_spot", "fungal", ["groundnut"],
   ("Late Leaf Spot", "Madoa ya Marehemu ya Majani (Late Leaf Spot)", "Cercosporiose tardive"),
   ("Nearly black, rough spots mostly on the underside of leaves, with little or no yellow halo; appears later in the season and causes heavy leaf drop.",
    "Madoa karibu meusi na yenye ukwaru hasa chini ya jani, yenye mduara wa njano kidogo au bila; huonekana baadaye msimuni na husababisha majani mengi kudondoka.",
    "Taches presque noires et rugueuses surtout sous la feuille, avec peu ou pas de halo jaune ; apparaît plus tard dans la saison et provoque une forte chute des feuilles."),
   now=["SCOUT"],
   cult=["AIRFLOW"],
   chem=["CHEM_PROTECTANT", "CHEM_SYSTEMIC"],
   prev=["RESISTANT", "ROTATE", "RESIDUE", "PLANT_EARLY", "CLEAN_SEED"],
   alias=["late leaf spot"])

_d("groundnut_rosette", "viral", ["groundnut"],
   ("Groundnut Rosette", "Rosette ya Karanga (Groundnut Rosette)", "Rosette de l'arachide"),
   ("Stunted plants with small, twisted leaves showing a yellow mosaic or a green rosette pattern; few or no pods; spread by aphids.",
    "Mimea iliyodumaa yenye majani madogo yaliyopinda yenye mosaic ya njano au rosette ya kijani; maganda machache au hakuna; huenezwa na vidukari.",
    "Plants nanifiés à petites feuilles tordues montrant une mosaïque jaune ou une rosette verte ; peu ou pas de gousses ; transmis par les pucerons."),
   now=["ROGUE", "CLEAR_WEEDS"],
   chem=["CHEM_NONE", "CHEM_VECTOR"],
   prev=["PLANT_EARLY", "DENSE_SPACING", "RESISTANT", "CLEAN_SEED"],
   alias=["groundnut rosette", "rosette"])

# ---- Coffee / tea -------------------------------------------------------
_d("coffee_leaf_rust", "fungal", ["coffee"],
   ("Coffee Leaf Rust", "Kutu ya Majani ya Kahawa (Coffee Leaf Rust)", "Rouille orangée du caféier"),
   ("Yellow-orange powdery spots under the leaves with pale yellow patches on top; severe attack causes leaf drop and dieback of branches.",
    "Madoa ya unga ya njano-machungwa chini ya majani na mabaka ya njano hafifu juu; shambulio kubwa husababisha majani kudondoka na matawi kukauka.",
    "Taches poudreuses jaune-orangé sous les feuilles avec plages jaune pâle dessus ; une forte attaque provoque la chute des feuilles et le dessèchement des rameaux."),
   now=["SCOUT"],
   cult=["PRUNE_SHADE", "BALANCED_FERT", "CLEAR_WEEDS"],
   chem=["CHEM_COFFEE", "CHEM_COPPER"],
   prev=["RESISTANT_COFFEE"],
   alias=["coffee leaf rust", "leaf rust coffee", "kutu ya kahawa", "rouille orangée", "clr"])

_d("coffee_berry_disease", "fungal", ["coffee"],
   ("Coffee Berry Disease", "Ugonjwa wa Matunda ya Kahawa (Coffee Berry Disease, CBD)", "Anthracnose des baies du caféier (CBD)"),
   ("Dark, sunken, scabby spots on green berries that spread and rot the berry; blossoms turn brown; berries drop or dry on the tree as 'mummies'.",
    "Madoa meusi yaliyozama yenye magamba kwenye matunda mabichi yanayoenea na kuoza tunda; maua hubadilika kuwa kahawia; matunda hudondoka au hukauka mtini.",
    "Taches sombres, enfoncées et croûteuses sur les baies vertes qui s'étendent et font pourrir la baie ; fleurs brunies ; baies tombées ou desséchées sur l'arbre (« momies »)."),
   now=["HARVEST_HYGIENE"],
   cult=["PRUNE_SHADE"],
   chem=["CHEM_COFFEE", "CHEM_COPPER"],
   prev=["RESISTANT_COFFEE"],
   alias=["coffee berry disease", "cbd", "berry disease", "anthracnose des baies"])

_d("blister_blight", "fungal", ["tea"],
   ("Blister Blight", "Ugonjwa wa Malengelenge ya Chai (Blister Blight)", "Cloque du théier"),
   ("Small translucent spots on young leaves that grow into pale blisters, then show a whitish spore layer underneath; young shoots become distorted.",
    "Madoa madogo yanayopenyeza mwanga kwenye majani machanga yanayokua kuwa malengelenge hafifu, kisha huonyesha safu nyeupe ya vimelea chini; machipukizi machanga hupinda.",
    "Petites taches translucides sur jeunes feuilles qui deviennent des cloques pâles, puis montrent une couche de spores blanchâtre dessous ; jeunes pousses déformées."),
   now=["REMOVE_LEAVES"],
   cult=["SHORT_PLUCK", "PRUNE_SHADE"],
   chem=["CHEM_COPPER", "CHEM_SYSTEMIC"],
   prev=["RESISTANT", "BALANCED_FERT"],
   alias=["blister blight", "malengelenge", "cloque"])

# ---- Banana -------------------------------------------------------------
_d("black_sigatoka", "fungal", ["banana"],
   ("Black Sigatoka", "Black Sigatoka (Madoa Meusi ya Majani ya Migomba)", "Cercosporiose noire (maladie des raies noires)"),
   ("Small reddish-brown streaks under the leaf that grow into dark, black-edged spots with grey centres; leaves die early and bunches are small and ripen unevenly.",
    "Michirizi midogo ya kahawia-nyekundu chini ya jani inayokua kuwa madoa meusi yenye kingo nyeusi na kituo cha kijivu; majani hufa mapema na mikungu ni midogo na huiva kwa kutofautiana.",
    "Petites stries brun-rouge sous la feuille qui deviennent des taches sombres à bord noir et centre gris ; feuilles mortes précocement, régimes petits et à maturation irrégulière."),
   now=["DELEAF"],
   cult=["AIRFLOW", "DRAINAGE", "BALANCED_FERT", "CLEAR_WEEDS"],
   chem=["CHEM_SYSTEMIC", "CHEM_PROTECTANT"],
   prev=["RESISTANT", "DELEAF"],
   alias=["black sigatoka", "sigatoka", "cercosporiose noire", "raies noires"])

_d("banana_xanthomonas_wilt", "bacterial", ["banana"],
   ("Banana Xanthomonas Wilt", "Mnyauko wa Xanthomonas wa Ndizi (Banana Xanthomonas Wilt, BXW)", "Flétrissement bactérien du bananier (Xanthomonas)"),
   ("Leaves yellow and wilt from the top, fruit ripens unevenly and rots inside with yellow-brown discolouration, and cut stems ooze yellow bacterial slime.",
    "Majani hugeuka njano na kunyauka kuanzia juu, matunda huiva kwa kutofautiana na kuoza ndani kwa rangi ya njano-kahawia, na shina lililokatwa hutoa ute wa njano wa bakteria.",
    "Feuilles jaunissant et flétrissant à partir du haut, fruits mûrissant irrégulièrement et pourrissant à l'intérieur (jaune-brun), tiges coupées laissant suinter un mucus bactérien jaune."),
   now=["REMOVE_MAT", "DISINFECT_TOOLS", "DEBUD", "RESTRICT_MOVEMENT", "REPORT"],
   chem=["CHEM_NONE"],
   prev=["CLEAN_CUTTINGS", "DEBUD", "DISINFECT_TOOLS"],
   report=True,
   alias=["banana xanthomonas wilt", "bxw", "banana wilt", "xanthomonas"])

_d("panama_disease", "fungal", ["banana"],
   ("Panama Disease", "Ugonjwa wa Panama (Panama Disease / Fusarium Wilt)", "Maladie de Panama (fusariose)"),
   ("Older leaves yellow from the edges and collapse around the stem like a skirt; the base of the stem splits and the inside shows brown-red streaks.",
    "Majani ya zamani hugeuka njano kuanzia pembeni na kuanguka kuzunguka shina kama sketi; sehemu ya chini ya shina hupasuka na ndani huonyesha michirizi ya kahawia-nyekundu.",
    "Vieilles feuilles jaunissant par les bords et s'affaissant autour du pseudo-tronc comme une jupe ; la base se fend et l'intérieur montre des stries brun-rouge."),
   now=["REMOVE_MAT", "RESTRICT_MOVEMENT", "REPORT"],
   chem=["CHEM_NONE"],
   prev=["CLEAN_CUTTINGS", "RESISTANT", "DRAINAGE"],
   report=True,
   alias=["panama disease", "panama", "fusarium wilt", "fusarium", "fusariose"])

# ---- Wheat --------------------------------------------------------------
_d("stem_rust", "fungal", ["wheat"],
   ("Stem Rust", "Kutu ya Shina (Stem Rust)", "Rouille noire (rouille des tiges)"),
   ("Dark red-brown, elongated pustules on stems, leaf sheaths and leaves that tear the skin open and release rust-coloured spores; heavy attack shrivels the grain.",
    "Vipele virefu vya kahawia-nyekundu iliyokolea kwenye mashina, ala za majani na majani vinavyopasua ngozi na kutoa vimelea vya rangi ya kutu; shambulio kubwa hunyauisha punje.",
    "Pustules allongées rouge-brun foncé sur tiges, gaines et feuilles qui déchirent l'épiderme et libèrent des spores rouille ; une forte attaque ride les grains."),
   now=["SCOUT", "REPORT"],
   cult=["CLEAR_WEEDS"],
   chem=["SPRAY_RUST", "CHEM_SYSTEMIC"],
   prev=["RESISTANT", "PLANT_EARLY", "CLEAR_WEEDS"],
   report=True,
   alias=["stem rust", "black rust", "ug99", "kutu ya shina", "rouille noire"])

_d("yellow_rust", "fungal", ["wheat"],
   ("Yellow Rust", "Kutu ya Njano (Yellow / Stripe Rust)", "Rouille jaune"),
   ("Bright yellow powdery stripes of pustules along the leaf veins in cool, humid weather; leaves dry out and yield drops.",
    "Michirizi ya unga wa njano angavu ya vipele kando ya mishipa ya jani wakati wa baridi na unyevu; majani hukauka na mavuno hupungua.",
    "Stries poudreuses jaune vif de pustules le long des nervures par temps frais et humide ; les feuilles sèchent et le rendement baisse."),
   now=["SCOUT"],
   cult=["CLEAR_WEEDS"],
   chem=["SPRAY_RUST", "CHEM_SYSTEMIC"],
   prev=["RESISTANT", "PLANT_EARLY", "CLEAR_WEEDS"],
   alias=["yellow rust", "stripe rust", "kutu ya njano", "rouille jaune"])

_d("leaf_rust", "fungal", ["wheat"],
   ("Leaf Rust", "Kutu ya Majani (Leaf Rust)", "Rouille brune du blé"),
   ("Small round orange-brown pustules scattered mostly on the upper leaf surface; leaves yellow and dry early.",
    "Vipele vidogo vya duara vya rangi ya machungwa-kahawia vilivyotawanyika hasa juu ya jani; majani hugeuka njano na kukauka mapema.",
    "Petites pustules rondes orange-brun dispersées surtout sur la face supérieure ; les feuilles jaunissent et sèchent tôt."),
   now=["SCOUT"],
   cult=["CLEAR_WEEDS"],
   chem=["SPRAY_RUST", "CHEM_SYSTEMIC"],
   prev=["RESISTANT", "PLANT_EARLY", "CLEAR_WEEDS"],
   alias=["leaf rust", "brown rust", "kutu ya majani", "rouille brune"])

# ---- Rice ---------------------------------------------------------------
_d("rice_blast", "fungal", ["rice"],
   ("Rice Blast", "Ugonjwa wa Blast wa Mpunga (Rice Blast)", "Pyriculariose du riz"),
   ("Diamond-shaped spots with grey centres and brown edges on leaves; the neck of the panicle can turn black and break (neck blast), leaving empty grains.",
    "Madoa yenye umbo la almasi yenye kituo cha kijivu na kingo za kahawia kwenye majani; shingo ya suke inaweza kuwa nyeusi na kukatika (neck blast), na kuacha punje tupu.",
    "Taches en losange au centre gris et bord brun sur les feuilles ; le col de la panicule peut noircir et casser (pyriculariose du col), laissant des grains vides."),
   now=["SCOUT"],
   cult=["BALANCED_FERT", "AIRFLOW"],
   chem=["CHEM_RICE"],
   prev=["RESISTANT", "CLEAN_SEED", "RESIDUE", "PLANT_EARLY"],
   alias=["rice blast", "blast", "pyriculariose"])

_d("bacterial_leaf_blight", "bacterial", ["rice"],
   ("Bacterial Leaf Blight", "Ukungu wa Bakteria wa Majani ya Mpunga (Bacterial Leaf Blight)", "Brûlure bactérienne du riz"),
   ("Water-soaked yellow-orange stripes starting at leaf tips and edges and running down the leaf; leaves look burnt and dry, with milky ooze in the morning.",
    "Michirizi yenye maji ya njano-machungwa inayoanzia ncha na kingo za jani na kushuka chini; majani huonekana kuchomeka na kukauka, na ute mweupe asubuhi.",
    "Stries jaune-orangé d'aspect huileux partant de la pointe et des bords et descendant sur la feuille ; feuilles d'aspect brûlé et desséché, avec exsudat laiteux le matin."),
   now=["ISOLATE", "HOLD_NITROGEN"],
   cult=["WATER_NO_FLOW", "BALANCED_FERT"],
   chem=["CHEM_NONE"],
   prev=["RESISTANT", "CLEAN_SEED", "RESIDUE", "CLEAR_WEEDS"],
   alias=["bacterial leaf blight", "blb", "brûlure bactérienne"])

_d("brown_spot", "fungal", ["rice"],
   ("Brown Spot", "Madoa ya Kahawia (Brown Spot)", "Helminthosporiose du riz (tache brune)"),
   ("Oval brown spots with a grey centre and yellow halo on leaves and grains; typical where plants are short of nutrients or water.",
    "Madoa ya kahawia ya mviringo yenye kituo cha kijivu na mduara wa njano kwenye majani na punje; hutokea sana pale mimea inapokosa virutubisho au maji.",
    "Taches ovales brunes au centre gris et halo jaune sur feuilles et grains ; typique des plants manquant d'éléments nutritifs ou d'eau."),
   cult=["BALANCED_FERT", "WATER_STRESS"],
   chem=["CHEM_PROTECTANT"],
   prev=["CLEAN_SEED", "RESIDUE", "RESISTANT"],
   alias=["brown spot", "tache brune"])

# ---- Cassava ------------------------------------------------------------
_d("cassava_mosaic_disease", "viral", ["cassava"],
   ("Cassava Mosaic Disease", "Ugonjwa wa Mosaic wa Mhogo (Cassava Mosaic Disease, CMD)", "Mosaïque du manioc (CMD)"),
   ("Leaves show a yellow-green mosaic with twisted, distorted small leaflets; plants are stunted and give few, small roots.",
    "Majani huonyesha mosaic ya njano-kijani na vijani vidogo vilivyopinda na kuharibika; mimea hudumaa na kutoa mizizi michache na midogo.",
    "Feuilles à mosaïque jaune-vert avec folioles petites, tordues et déformées ; plants nanifiés produisant peu de racines, petites."),
   now=["ROGUE", "SCOUT"],
   cult=["CLEAN_CUTTINGS", "CLEAR_WEEDS"],
   chem=["CHEM_NONE"],
   prev=["RESISTANT", "CLEAN_CUTTINGS"],
   alias=["cassava mosaic", "cmd", "mosaic", "batobato", "mosaïque du manioc"])

_d("cassava_brown_streak_disease", "viral", ["cassava"],
   ("Cassava Brown Streak Disease", "Ugonjwa wa Michirizi ya Kahawia ya Mhogo (Cassava Brown Streak Disease, CBSD)", "Striure brune du manioc (CBSD)"),
   ("Yellow feathery patches along veins of mature leaves, brown streaks on green stems, and brown corky rot inside the roots even when the plant looks fine above ground.",
    "Mabaka ya njano kama manyoya kando ya mishipa ya majani yaliyokomaa, michirizi ya kahawia kwenye mashina ya kijani, na uozo wa kahawia wenye ugumu ndani ya mizizi hata mmea ukionekana mzima juu ya ardhi.",
    "Plages jaunes en plumes le long des nervures des feuilles adultes, stries brunes sur tiges vertes et pourriture brune liégeuse à l'intérieur des racines même si la plante paraît saine en surface."),
   now=["ROGUE", "REPORT", "RESTRICT_MOVEMENT"],
   cult=["HARVEST_EARLY", "CLEAN_CUTTINGS"],
   chem=["CHEM_NONE"],
   prev=["RESISTANT", "CLEAN_CUTTINGS"],
   report=True,
   alias=["cassava brown streak", "cbsd", "brown streak", "michirizi ya kahawia", "striure brune"])

_d("cassava_bacterial_blight", "bacterial", ["cassava"],
   ("Cassava Bacterial Blight", "Ukungu wa Bakteria wa Mhogo (Cassava Bacterial Blight)", "Bactériose du manioc"),
   ("Angular water-soaked leaf spots that turn brown, leaf wilting and blight, gum oozing from stems and dieback of shoot tips.",
    "Madoa yenye pembe na maji kwenye majani yanayogeuka kahawia, majani kunyauka na kukauka, utomvu kutoka kwenye mashina na ncha za machipukizi kufa.",
    "Taches foliaires anguleuses d'aspect huileux qui brunissent, flétrissement et brûlure des feuilles, gomme suintant des tiges et dessèchement des extrémités des pousses."),
   now=["REMOVE_LEAVES", "DISINFECT_TOOLS", "ISOLATE"],
   cult=["RESIDUE", "CLEAN_CUTTINGS"],
   chem=["CHEM_NONE"],
   prev=["RESISTANT", "CLEAN_CUTTINGS", "ROTATE"],
   alias=["cassava bacterial blight", "cbb", "bactériose du manioc"])

_d("cassava_green_mite", "pest", ["cassava"],
   ("Cassava Green Mite", "Utitiri wa Kijani wa Mhogo (Cassava Green Mite)", "Acarien vert du manioc"),
   ("Tiny yellow-green speckles at the shoot tips, then stunted, shrunken, yellow-mottled and deformed young leaves; severe attack causes leaf drop in the dry season.",
    "Vitone vidogo vya njano-kijani kwenye ncha za machipukizi, kisha majani machanga yaliyodumaa, kunywea, yenye mabaka ya njano na kuharibika; shambulio kubwa husababisha majani kudondoka wakati wa kiangazi.",
    "Minuscules ponctuations jaune-vert aux extrémités des pousses, puis jeunes feuilles rabougries, ratatinées, marbrées de jaune et déformées ; une forte attaque provoque la chute des feuilles en saison sèche."),
   now=["BIO_ENEMIES"],
   cult=["MULCH", "WATER_STRESS"],
   chem=["CHEM_AVOID_MITE_ENEMIES"],
   prev=["RESISTANT", "PLANT_EARLY", "CLEAN_CUTTINGS"],
   alias=["cassava green mite", "green mite", "green mottle", "utitiri wa mhogo", "acarien vert"])

# ---- Cocoa --------------------------------------------------------------
_d("black_pod_blight", "fungal", ["cocoa"],
   ("Black Pod Blight", "Ugonjwa wa Maganda Meusi ya Kakao (Black Pod)", "Pourriture brune des cabosses (Black Pod)"),
   ("Brown to black spots on pods that spread quickly over the whole pod, often with white mould in humid weather; infected pods rot and the beans are spoiled.",
    "Madoa ya kahawia hadi meusi kwenye maganda yanayoenea haraka kwenye ganda zima, mara nyingi na ukungu mweupe wakati wa unyevu; maganda yaliyoambukizwa huoza na mbegu huharibika.",
    "Taches brunes à noires sur les cabosses qui gagnent vite toute la cabosse, souvent avec moisissure blanche par temps humide ; les cabosses pourrissent et les fèves sont perdues."),
   now=["HARVEST_HYGIENE"],
   cult=["PRUNE_SHADE", "CLEAR_WEEDS", "DRAINAGE"],
   chem=["CHEM_POD"],
   prev=["RESISTANT", "HARVEST_HYGIENE"],
   alias=["black pod", "black pod blight", "pourriture brune", "maganda meusi"])

_d("cocoa_swollen_shoot_virus", "viral", ["cocoa"],
   ("Cocoa Swollen Shoot Virus", "Virusi vya Uvimbe wa Machipukizi ya Kakao (Cocoa Swollen Shoot Virus)", "Virus du swollen shoot du cacaoyer (CSSV)"),
   ("Red vein-banding in young leaves, swellings on stems and roots and fewer pods; trees decline and die within a few years; spread by mealybugs.",
    "Mishipa myekundu kwenye majani machanga, uvimbe kwenye mashina na mizizi na maganda machache; miti hudhoofika na kufa ndani ya miaka michache; huenezwa na mealybugs.",
    "Bandes rouges le long des nervures des jeunes feuilles, gonflements sur tiges et racines et peu de cabosses ; les arbres dépérissent et meurent en quelques années ; transmis par des cochenilles."),
   now=["REPORT", "RESTRICT_MOVEMENT"],
   cult=["CSSV_OFFICIAL", "CLEAR_WEEDS"],
   chem=["CHEM_NONE"],
   prev=["RESISTANT", "CLEAN_SEED"],
   report=True,
   alias=["swollen shoot", "cssv", "cocoa swollen shoot virus", "gonflement"])

# ---- Brassicas ----------------------------------------------------------
_d("black_rot", "bacterial", ["brassica"],
   ("Black Rot", "Kuoza Kuu Mweusi (Black Rot)", "Pourriture noire des crucifères"),
   ("Yellow V-shaped patches starting at the leaf edge with blackened veins; leaves wither and heads rot, often with a bad smell.",
    "Mabaka ya njano yenye umbo la V yanayoanzia pembeni mwa jani na mishipa iliyogeuka nyeusi; majani hunyauka na vichwa huoza, mara nyingi na harufu mbaya.",
    "Plages jaunes en V partant du bord de la feuille avec nervures noircies ; les feuilles flétrissent et les pommes pourrissent, souvent avec une mauvaise odeur."),
   now=["REMOVE_LEAVES", "ISOLATE", "DISINFECT_TOOLS"],
   cult=["AVOID_WET_WORK", "CLEAR_WEEDS"],
   chem=["CHEM_COPPER"],
   prev=["CLEAN_SEED", "HOT_WATER_SEED", "ROTATE", "RESISTANT", "RESIDUE"],
   alias=["black rot", "kuoza kuu", "pourriture noire"])

_d("diamondback_moth", "pest", ["brassica"],
   ("Diamondback Moth", "Kiwavi wa Kabichi (Diamondback Moth)", "Teigne des crucifères"),
   ("Small holes and 'window' scraping on leaves made by slender green caterpillars that wriggle when touched and hide in the heart of the plant.",
    "Mashimo madogo na ukwaruzaji kama 'dirisha' kwenye majani unaosababishwa na viwavi wembamba wa kijani wanaotingisika wakiguswa na kujificha moyoni mwa mmea.",
    "Petits trous et grattages en « fenêtres » sur les feuilles causés par de fines chenilles vertes qui se tortillent au toucher et se cachent au cœur de la plante."),
   now=["SCOUT", "REMOVE_LEAVES"],
   cult=["CLEAR_WEEDS"],
   bio=["BIO_BT", "BIO_NEEM", "BIO_ENEMIES", "TRAPS"],
   chem=["CHEM_CATERPILLAR"],
   prev=["RESIDUE", "ROTATE"],
   alias=["diamondback moth", "diamondback", "dbm", "kiwavi wa kabichi", "teigne"])

_d("downy_mildew", "fungal", ["brassica", "spiderplant", "nightshade", "cowpea"],
   ("Downy Mildew", "Ukungu wa Unga Chini ya Majani (Downy Mildew)", "Mildiou"),
   ("Yellow angular patches on the upper leaf surface with fluffy white-grey mould underneath in cool, humid conditions.",
    "Mabaka ya njano yenye pembe juu ya jani na ukungu laini mweupe-kijivu chini ya jani wakati wa baridi na unyevu.",
    "Plages jaunes anguleuses sur la face supérieure avec un duvet blanc-gris dessous par temps frais et humide."),
   now=["REMOVE_LEAVES"],
   cult=["AIRFLOW", "AVOID_WET_WORK"],
   chem=["CHEM_COPPER", "CHEM_PROTECTANT"],
   prev=["RESISTANT", "ROTATE", "RESIDUE", "CLEAN_SEED"],
   alias=["downy mildew", "mildiou"])

_d("powdery_mildew", "fungal", ["brassica", "cowpea", "tomato", "beans", "spiderplant", "nightshade"],
   ("Powdery Mildew", "Ukungu wa Unga (Powdery Mildew)", "Oïdium"),
   ("White powdery patches on leaves and young stems that spread and cover the leaf; leaves yellow, curl and dry.",
    "Mabaka meupe ya unga kwenye majani na mashina machanga yanayoenea na kufunika jani; majani hugeuka njano, hujikunja na kukauka.",
    "Plages blanches poudreuses sur feuilles et jeunes tiges qui s'étendent et couvrent la feuille ; feuilles jaunissantes, enroulées puis desséchées."),
   now=["REMOVE_LEAVES"],
   cult=["AIRFLOW", "BALANCED_FERT"],
   bio=["BIO_TRICHO"],
   chem=["CHEM_SULPHUR", "CHEM_SYSTEMIC"],
   prev=["RESISTANT", "AIRFLOW"],
   alias=["powdery mildew", "oidium", "oïdium", "ukungu wa unga"])

# ---- Yam / generic ------------------------------------------------------
_d("yam_anthracnose", "fungal", ["yam"],
   ("Yam Anthracnose", "Anthracnose ya Viazi Vikuu (Yam Anthracnose)", "Anthracnose de l'igname"),
   ("Dark brown to black spots with yellow halos on leaves that join together; vines die back from the tips and leaves look scorched.",
    "Madoa ya kahawia iliyokolea hadi nyeusi yenye mduara wa njano kwenye majani yanayoungana; mizabibu hukauka kuanzia ncha na majani huonekana kuungua.",
    "Taches brun foncé à noires avec halo jaune sur les feuilles qui fusionnent ; les lianes dessèchent à partir des extrémités et les feuilles paraissent brûlées."),
   now=["REMOVE_LEAVES", "SCOUT"],
   cult=["AIRFLOW", "CLEAR_WEEDS"],
   chem=["CHEM_PROTECTANT", "CHEM_COPPER"],
   prev=["CLEAN_SEED", "RESISTANT", "ROTATE", "RESIDUE"],
   alias=["yam anthracnose", "anthracnose de l'igname"])

_d("leaf_spot", "fungal", [],
   ("Leaf Spot", "Madoa ya Majani (Leaf Spot)", "Taches foliaires"),
   ("Round to irregular brown or black spots on leaves, sometimes with a yellow halo; the cause may be a fungus or a bacterium, so the exact disease is uncertain.",
    "Madoa ya duara hadi yasiyo na umbo maalum ya kahawia au nyeusi kwenye majani, mara nyingine na mduara wa njano; kisababishi kinaweza kuwa kuvu au bakteria, kwa hiyo ugonjwa kamili haujulikani.",
    "Taches rondes à irrégulières brunes ou noires sur les feuilles, parfois avec un halo jaune ; la cause peut être un champignon ou une bactérie, la maladie exacte reste donc incertaine."),
   now=["REMOVE_LEAVES", "ISOLATE", "CONFIRM"],
   cult=["AVOID_WET_WORK", "AIRFLOW", "MULCH"],
   chem=["CHEM_COPPER"],
   prev=["ROTATE", "RESIDUE", "CLEAN_SEED"],
   alias=["leaf spot", "madoa ya majani", "taches foliaires"])
