"""BUG-013: демо-база в localStorage не теряет записи, когда две вкладки пишут одновременно."""

N = 15
# Запускаем запись и сразу возвращаемся: обе вкладки пишут одновременно, результат забираем потом
FIRE = """([n, tag]) => {
  const jobs = [];
  for (let i = 0; i < n; i++) jobs.push(PortfolioAPI.createLead('cafe', { kind: 'table', name: `${tag}-${i}`, phone: '+79001234567' }));
  window.__ids = Promise.all(jobs).then((rs) => rs.map((r) => r.id));
}"""


def test_two_tabs_keep_all_leads(context, site):
    a, b = context.new_page(), context.new_page()
    for p in (a, b):
        p.goto(f"{site}/projects/cafe/")
    a.evaluate(FIRE, [N, "A"])
    b.evaluate(FIRE, [N, "B"])
    got = [a.evaluate("() => window.__ids"), b.evaluate("() => window.__ids")]
    all_ids = got[0] + got[1]
    assert len(set(all_ids)) == 2 * N, "Две вкладки выдали один id"
    a.wait_for_timeout(300)
    names = a.evaluate("() => JSON.parse(localStorage.getItem('pf-db-v1')).leads.map((l) => l.name)")
    for tag in "AB":
        assert sum(n.startswith(f"{tag}-") for n in names) == N, f"Пропали заявки вкладки {tag}"
