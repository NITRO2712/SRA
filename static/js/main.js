document.addEventListener('DOMContentLoaded', () => {
  // Live marks total calculation
  const marksInputs = document.querySelectorAll('.marks-input');
  marksInputs.forEach(input => {
    input.addEventListener('input', (e) => {
      const row = e.target.closest('tr');
      if (row) {
        const internal = parseInt(row.querySelector('.internal-input')?.value || 0);
        const external = parseInt(row.querySelector('.external-input')?.value || 0);
        const totalSpan = row.querySelector('.total-marks-span');
        if (totalSpan) {
          totalSpan.textContent = internal + external;
        }
      }
    });
  });

  // Render Charts if on analysis page
  if (document.getElementById('subjectAvgChart')) {
    loadAnalysisCharts();
  }
});

async function loadAnalysisCharts() {
  try {
    const res = await fetch('/api/analysis-data');
    const data = await res.json();

    // 1. Subject Average & Pass Percentage Chart
    const ctx1 = document.getElementById('subjectAvgChart').getContext('2d');
    new Chart(ctx1, {
      type: 'bar',
      data: {
        labels: data.subjects,
        datasets: [
          {
            label: 'Average Marks',
            data: data.averages,
            backgroundColor: 'rgba(99, 102, 241, 0.7)',
            borderColor: '#6366f1',
            borderWidth: 2,
            borderRadius: 6
          },
          {
            label: 'Highest Marks',
            data: data.highest,
            backgroundColor: 'rgba(16, 185, 129, 0.7)',
            borderColor: '#10b981',
            borderWidth: 2,
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#9ca3af' } }
        },
        scales: {
          x: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } },
          y: { ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255, 255, 255, 0.05)' }, max: 100 }
        }
      }
    });

    // 2. Grade Distribution Doughnut Chart
    const ctx2 = document.getElementById('gradeDistChart').getContext('2d');
    const gradeLabels = Object.keys(data.grades);
    const gradeValues = Object.values(data.grades);
    
    new Chart(ctx2, {
      type: 'doughnut',
      data: {
        labels: gradeLabels,
        datasets: [{
          data: gradeValues,
          backgroundColor: [
            '#10b981', // O
            '#06b6d4', // A+
            '#3b82f6', // A
            '#8b5cf6', // B+
            '#f59e0b', // B
            '#d97706', // C
            '#ef4444'  // F
          ],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { color: '#9ca3af' } }
        }
      }
    });

  } catch (err) {
    console.error('Failed to load chart data:', err);
  }
}
