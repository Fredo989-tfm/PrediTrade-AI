const { onRequest } = require("firebase-functions/v2/https");
const admin = require("firebase-admin");
const crypto = require("crypto");

admin.initializeApp();

const db = admin.firestore();

/* =========================
   🔐 UTILITAIRES UTILISATEURS
   ========================= */

function normalizeEmail(email) {
  return String(email || "").trim().toLowerCase();
}

function hashPassword(password) {
  return crypto
    .createHash("sha256")
    .update(String(password))
    .digest("hex");
}

function validEmail(email) {
  return typeof email === "string" &&
    email.includes("@") &&
    email.includes(".");
}

/* =========================
   👤 INSCRIPTION UTILISATEUR
   ========================= */

exports.registerUser = onRequest(
  {
    region: "europe-west1",
    cors: true,
  },
  async (req, res) => {
    try {
      if (req.method !== "POST") {
        return res.status(405).json({
          success: false,
          error: "Méthode non autorisée."
        });
      }

      const { email, password } = req.body || {};

      const normalizedEmail = normalizeEmail(email);

      if (!validEmail(normalizedEmail)) {
        return res.status(400).json({
          success: false,
          error: "Adresse email invalide."
        });
      }

      if (!password || String(password).length < 6) {
        return res.status(400).json({
          success: false,
          error: "Le mot de passe doit contenir au moins 6 caractères."
        });
      }

      const userRef = db
        .collection("users")
        .doc(normalizedEmail);

      const existingUser = await userRef.get();

      if (existingUser.exists) {
        return res.status(409).json({
          success: false,
          error: "Cet email existe déjà."
        });
      }

      const user = {
        email: normalizedEmail,
        password: hashPassword(password),
        premium: false,
        trialUsed: false,
        createdAt: admin.firestore.FieldValue.serverTimestamp()
      };

      await userRef.set(user);

      console.log(`👤 Nouveau compte créé : ${normalizedEmail}`);

      return res.status(200).json({
        success: true,
        message: "Compte créé avec succès.",
        email: normalizedEmail
      });

    } catch (error) {
      console.error("❌ Erreur registerUser:", error);

      return res.status(500).json({
        success: false,
        error: "Erreur interne du serveur."
      });
    }
  }
);


/* =========================
   🔑 CONNEXION UTILISATEUR
   ========================= */

exports.loginUser = onRequest(
  {
    region: "europe-west1",
    cors: true,
  },
  async (req, res) => {
    try {
      if (req.method !== "POST") {
        return res.status(405).json({
          success: false,
          error: "Méthode non autorisée."
        });
      }

      const { email, password } = req.body || {};

      const normalizedEmail = normalizeEmail(email);

      if (!validEmail(normalizedEmail) || !password) {
        return res.status(400).json({
          success: false,
          error: "Email ou mot de passe invalide."
        });
      }

      const userRef = db
        .collection("users")
        .doc(normalizedEmail);

      const snapshot = await userRef.get();

      if (!snapshot.exists) {
        return res.status(401).json({
          success: false,
          error: "Email ou mot de passe incorrect."
        });
      }

      const user = snapshot.data();

      const passwordHash = hashPassword(password);

      if (passwordHash !== user.password) {
        return res.status(401).json({
          success: false,
          error: "Email ou mot de passe incorrect."
        });
      }

      return res.status(200).json({
        success: true,
        message: "Connexion réussie.",
        email: normalizedEmail,
        premium: user.premium === true,
        trialUsed: user.trialUsed === true
      });

    } catch (error) {
      console.error("❌ Erreur loginUser:", error);

      return res.status(500).json({
        success: false,
        error: "Erreur interne du serveur."
      });
    }
  }
);


/* =========================
   👤 RÉCUPÉRER UN UTILISATEUR
   ========================= */

exports.getUser = onRequest(
  {
    region: "europe-west1",
    cors: true,
  },
  async (req, res) => {
    try {
      if (req.method !== "POST") {
        return res.status(405).json({
          success: false,
          error: "Méthode non autorisée."
        });
      }

      const { email } = req.body || {};
      const normalizedEmail = normalizeEmail(email);

      if (!validEmail(normalizedEmail)) {
        return res.status(400).json({
          success: false,
          error: "Email invalide."
        });
      }

      const snapshot = await db
        .collection("users")
        .doc(normalizedEmail)
        .get();

      if (!snapshot.exists) {
        return res.status(404).json({
          success: false,
          error: "Utilisateur introuvable."
        });
      }

      const user = snapshot.data();

      return res.status(200).json({
        success: true,
        email: normalizedEmail,
        premium: user.premium === true,
        trialUsed: user.trialUsed === true
      });

    } catch (error) {
      console.error("❌ Erreur getUser:", error);

      return res.status(500).json({
        success: false,
        error: "Erreur interne du serveur."
      });
    }
  }
);


/* =========================
   🔔 CRÉER UNE NOTIFICATION
   ========================= */

function validateNotification(data) {
  if (!data) return "Données manquantes.";
  if (!data.userId) return "userId manquant.";
  if (!data.asset) return "asset manquant.";
  if (typeof data.score !== "number") return "score invalide.";
  if (!data.signal) return "signal manquant.";

  return null;
}

exports.createNotification = onRequest(
  {
    region: "europe-west1",
    cors: true,
  },
  async (req, res) => {
    try {
      if (req.method !== "POST") {
        return res.status(405).json({
          success: false,
          error: "Méthode non autorisée. Utilisez POST."
        });
      }

      const data = req.body;

      const validationError = validateNotification(data);

      if (validationError) {
        return res.status(400).json({
          success: false,
          error: validationError
        });
      }

      const notification = {
        userId: data.userId,
        asset: data.asset,
        score: Number(data.score),
        signal: data.signal,
        confidence: data.confidence || "Non définie",
        price: data.price || null,
        message:
          data.message ||
          `${data.asset} — ${data.signal} — PrediScore ${data.score}/100`,
        type: data.type || "opportunity",
        read: false,
        createdAt: admin.firestore.FieldValue.serverTimestamp()
      };

      const notificationRef = await db
        .collection("notifications")
        .add(notification);

      console.log(
        `🔔 Notification créée : ${notificationRef.id}`
      );

      return res.status(200).json({
        success: true,
        notificationId: notificationRef.id,
        message: "Notification créée avec succès."
      });

    } catch (error) {
      console.error(
        "❌ Erreur createNotification:",
        error
      );

      return res.status(500).json({
        success: false,
        error: "Erreur interne du serveur."
      });
    }
  }
);


/* =========================
   ❤️ MARQUER NOTIFICATION LUE
   ========================= */

exports.markNotificationRead = onRequest(
  {
    region: "europe-west1",
    cors: true,
  },
  async (req, res) => {
    try {
      if (req.method !== "POST") {
        return res.status(405).json({
          success: false,
          error: "Méthode non autorisée."
        });
      }

      const { notificationId } = req.body || {};

      if (!notificationId) {
        return res.status(400).json({
          success: false,
          error: "notificationId manquant."
        });
      }

      await db
        .collection("notifications")
        .doc(notificationId)
        .update({
          read: true,
          readAt: admin.firestore.FieldValue.serverTimestamp()
        });

      return res.status(200).json({
        success: true,
        message: "Notification marquée comme lue."
      });

    } catch (error) {
      console.error(
        "❌ Erreur markNotificationRead:",
        error
      );

      return res.status(500).json({
        success: false,
        error: "Impossible de modifier la notification."
      });
    }
  }
);


/* =========================
   🧪 HEALTH CHECK
   ========================= */

exports.healthCheck = onRequest(
  {
    region: "europe-west1",
    cors: true,
  },
  async (req, res) => {
    return res.status(200).json({
      success: true,
      service: "PrediTrade AI",
      status: "online",
      version: "5.0.0"
    });
  }
);
