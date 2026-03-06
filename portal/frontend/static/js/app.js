const state = {
  user: null,
  docs: [
    { id: 1, source_doc_id: 'DOC-00001', doc_name: '42 Oak Road - Tenancy Agreement 1', property_id: 1, property_address: '42 Oak Road, Harlow', tenant: 'John Smith', document_type: 'Tenancy Agreement', status: 'Verified', date: '2026-02-21', pdf_path: 'C:/ScanSystem_v2/Clients/Belvoir/Batches/2026-02-21/DOC-00001/document.pdf', fields: { landlord_name: 'ABC Properties Ltd', monthly_rent_amount: '£1,200' } },
    { id: 2, source_doc_id: 'DOC-00017', doc_name: '14 Mill Lane - Gas Safety', property_id: 2, property_address: '14 Mill Lane, Harlow', tenant: 'Sarah Miles', document_type: 'Gas Safety Certificate', status: 'Verified', date: '2026-02-24', pdf_path: 'C:/ScanSystem_v2/Clients/Belvoir/Batches/2026-02-24/DOC-00017/document.pdf', fields: { expiry_date: '2026-03-10', engineer_name: 'D. Carter' } },
    { id: 3, source_doc_id: 'DOC-00023', doc_name: '14 Mill Lane - EPC', property_id: 2, property_address: '14 Mill Lane, Harlow', tenant: 'Sarah Miles', document_type: 'EPC', status: 'Needs Review', date: '2026-03-02', pdf_path: 'C:/ScanSystem_v2/Clients/Belvoir/Batches/2026-03-02/DOC-00023/document.pdf', fields: { valid_until: '2026-03-01', current_rating: 'C' } }
  ],
  compliance: [
    { record_type: 'gas_safety_expiry', property_address: '14 Mill Lane, Harlow', expiry_date: '2026-03-10', status: 'expiring_soon' },
    { record_type: 'epc_expiry', property_address: '14 Mill Lane, Harlow', expiry_date: '2026-03-01', status: 'expired' },
    { record_type: 'tenancy_end', property_address: '42 Oak Road, Harlow', expiry_date: '2026-12-31', status: 'valid' }
  ],
};

function init() {
  bindNav();
  bindLogin();
  bindFilters();
  renderFilters();
  renderDocs(state.docs);
  renderProperties();
  renderCompliance();
}

function bindNav() {
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
      document.getElementById(btn.dataset.panel).classList.add('active');
      document.getElementById('panel-title').textContent = btn.textContent;
    });
  });
}

function bindLogin() {
  document.getElementById('login-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value.trim();
    state.user = email || 'demo@morphiq.co.uk';
    document.getElementById('user-label').textContent = state.user;
    document.getElementById('login-modal').classList.remove('active');
  });
}

function bindFilters() {
  document.getElementById('apply-filters').addEventListener('click', () => {
    const q = document.getElementById('q').value.toLowerCase();
    const propertyId = document.getElementById('property-filter').value;
    const tenant = document.getElementById('tenant-filter').value.toLowerCase();

    const filtered = state.docs.filter(doc => {
      const matchesQ = !q || [doc.doc_name, doc.source_doc_id, doc.property_address, doc.document_type].join(' ').toLowerCase().includes(q);
      const matchesProperty = !propertyId || String(doc.property_id) === propertyId;
      const matchesTenant = !tenant || (doc.tenant || '').toLowerCase().includes(tenant);
      return matchesQ && matchesProperty && matchesTenant;
    });

    renderDocs(filtered);
  });
}

function renderFilters() {
  const select = document.getElementById('property-filter');
  const properties = [...new Map(state.docs.map(d => [d.property_id, d.property_address])).entries()];
  select.innerHTML = '<option value="">All properties</option>' + properties.map(([id, address]) => `<option value="${id}">${address}</option>`).join('');
}

function renderDocs(docs) {
  const tbody = document.getElementById('documents-table');
  tbody.innerHTML = docs.map(doc => `
    <tr data-id="${doc.id}">
      <td>${doc.source_doc_id}</td>
      <td>${doc.doc_name}</td>
      <td>${doc.property_address}</td>
      <td>${doc.tenant || '-'}</td>
      <td>${doc.document_type}</td>
      <td>${doc.status}</td>
      <td>${doc.date}</td>
    </tr>
  `).join('');

  tbody.querySelectorAll('tr').forEach(row => {
    row.addEventListener('click', () => showDocument(Number(row.dataset.id)));
  });
}

function showDocument(docId) {
  const doc = state.docs.find(d => d.id === docId);
  if (!doc) return;

  document.querySelector('[data-panel="viewer-panel"]').click();
  document.getElementById('viewer-name').textContent = `${doc.doc_name} (${doc.source_doc_id})`;
  document.getElementById('viewer-details').textContent = `${doc.property_address} • ${doc.document_type} • ${doc.status}`;
  document.getElementById('viewer-placeholder').textContent = `PDF path: ${doc.pdf_path}`;
  document.getElementById('viewer-fields').innerHTML = Object.entries(doc.fields || {})
    .map(([k, v]) => `<p><strong>${k.replaceAll('_', ' ')}:</strong> ${v}</p>`)
    .join('');
}

function renderProperties() {
  const container = document.getElementById('property-cards');
  const grouped = {};
  state.docs.forEach(doc => {
    grouped[doc.property_address] ??= { total: 0, verified: 0, tenant: doc.tenant };
    grouped[doc.property_address].total += 1;
    if (doc.status === 'Verified') grouped[doc.property_address].verified += 1;
  });

  container.innerHTML = Object.entries(grouped).map(([address, summary]) => `
    <article class="card">
      <h4>${address}</h4>
      <p>Tenant: ${summary.tenant || 'N/A'}</p>
      <p>Total documents: ${summary.total}</p>
      <p>Verified: ${summary.verified}</p>
    </article>
  `).join('');
}

function renderCompliance() {
  const root = document.getElementById('compliance-alerts');
  root.innerHTML = state.compliance.map(item => `
    <article class="alert ${item.status}">
      <strong>${item.record_type}</strong> — ${item.property_address}<br>
      Expiry: ${item.expiry_date} · <span class="badge ${item.status}">${item.status}</span>
    </article>
  `).join('');
}

window.addEventListener('DOMContentLoaded', init);
