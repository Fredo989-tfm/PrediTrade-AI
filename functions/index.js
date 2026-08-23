const { onRequest } = require("firebase-functions/v2/https");
const admin = require("firebase-admin");

admin.initializeApp();

const db = admin.firestore();

/**
 * 🔔 PREDITRADE AI — SYSTÈME DE NOTIFICATIONS
 *
 * Reçoit une notification depuis PrediTrade AI
 * et l'enregistre dans Firestore.
 *
 * Données attendues :
 * {
 *   userId: "ID_UTILISATEUR",
 *   asset: "Bitcoin (BTC)",
 *   score: 90,
 *   signal: "🟢 ACHAT FORT",
 *   confidence: "Très élevée",
 *   price: 76990.17,
 *   message: "Opportunité détectée"
 * }
 */

// Vérification simple de la requête
function validateNotification(data) {
  if (!data) {
    return "Données manquantes.";
  }

  if (!data.userId) {
    return "userId manquant.";
  }

  if (!data.asset) {
    return "asset manquant.";
  }

  if (typeof data.score !== "number") {
    return "score invalide.";
  }

  if (!data.signal) {
    return "signal manquant.";
  }

  return null;
}


/**
 * 🔔 Créer une notification
 */
exports.createNotification = onRequest(
  {
    region: "europe-west1",
    cors: true,
  },
  async (req, res) => {

    try {

      // Autoriser uniquement POST
      if (req.method !== "POST") {
        return res.status(405).json({
          success: false,
          error: "Méthode non autorisée. Utilisez POST."
        });
      }

      const data = req.body;

      // Validation
      const validationError = validateNotification(data);

      if (validationError) {
        return res.status(400).json({
          success: false,
          error: validationError
        });
      }

      // Préparation de la notification
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

      // Enregistrement Firestore
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


/**
 * ❤️ Marquer une notification comme lue
 */
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

      const { notificationId } = req.body;

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


/**
 * 🧪 Vérification du fonctionnement de Firebase
 */
exports.healthCheck = onRequest(
  {
    region: "europe-west1",
    cors: true,
  },
  async (req, res) => {

    return res.status(200).json({
      success: true,
      service: "PrediTrade AI Notifications",
      status: "online",
      version: "5.0.0"
    });

  }
);
