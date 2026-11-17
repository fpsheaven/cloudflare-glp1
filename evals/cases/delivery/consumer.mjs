export async function queue(batch, env) {
  for (const message of batch.messages) {
    await env.sendNotification(message.body.recipient, message.body.text);
    await env.DB.prepare('INSERT INTO receipts(id) VALUES (?) ON CONFLICT(id) DO NOTHING')
      .bind(message.id).run();
  }
}
