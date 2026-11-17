export async function counts(env, owner) {
  return env.DB.prepare('SELECT COUNT(*) AS n FROM events WHERE owner = ?').bind(owner).first();
}

export async function save(env, id, owner, time, payload) {
  return env.DB.prepare('INSERT INTO events(id, owner, created, payload) VALUES(?,?,?,?) ON CONFLICT(id) DO NOTHING')
    .bind(id, owner, time, payload).run();
}
