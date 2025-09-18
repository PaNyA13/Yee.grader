#include <bits/stdc++.h>
using namespace std;

long long gcd(long long a, long long b) {
    return b == 0 ? llabs(a) : gcd(b, a % b);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;

    long long num = 0, den = 1; // sum = num/den

    for (int i = 0; i < N; ++i) {
        long long Si, Mi;
        cin >> Si >> Mi;

        // num/den + Si/Mi = (num*Mi + Si*den) / (den*Mi)
        num = num * Mi + Si * den;
        den = den * Mi;

        long long g = gcd(llabs(num), llabs(den));
        if (g != 0) {
            num /= g;
            den /= g;
        }
    }

    long long integer_part = 0, frac_num = 0, frac_den = 0;
    if (den != 0) {
        integer_part = num / den;
        frac_num = num % den;
        if (frac_num < 0) frac_num = -frac_num; // not needed here, but safe
        frac_den = den;

        if (frac_num != 0) {
            long long g = gcd(frac_num, frac_den);
            frac_num /= g;
            frac_den /= g;
        } else {
            // fractional part is zero -> print denominator as 0 per problem requirement
            frac_den = 0;
        }
    }

    cout << integer_part << " " << frac_num << " " << frac_den << "\n";
    return 0;
}
