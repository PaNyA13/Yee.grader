#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, K;
    if (!(cin >> N >> K)) return 0;
    vector<long long> h(N+1, 1); // 1-indexed, เริ่มต้นความสูง = 1

    for (int t = 0; t < K; ++t) {
        int Ci, Di;
        cin >> Ci >> Di;
        // ระยะที่เสียงส่งผลคือ D-1 เมืองทั้งสองด้าน ดังนั้น j ใน [Ci-(Di-1), Ci+(Di-1)]
        int L = max(1, Ci - (Di - 1));
        int R = min(N, Ci + (Di - 1));
        for (int j = L; j <= R; ++j) {
            int add = Di - abs(Ci - j);
            if (add > 0) h[j] += add;
        }
    }

    // หาค่าสูงสุด
    long long mx = *max_element(h.begin() + 1, h.end());

    // พิมพ์ดัชนีที่มีค่าสูงสุด คั่นด้วยช่องว่าง
    bool first = true;
    for (int i = 1; i <= N; ++i) {
        if (h[i] == mx) {
            if (!first) cout << ' ';
            cout << i;
            first = false;
        }
    }
    cout << '\n';
    return 0;
}
